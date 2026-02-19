/**
 * Cloudflare Pages Function - Instagram 계정 상태 확인
 *
 * Instagram 프로필 HTML 페이지의 og:* 메타태그를 파싱하여
 * 계정 상태와 프로필 사진을 가져옵니다.
 *
 * 429 응답 시 아래 순서로 fallback합니다:
 *   1. Google Cloud Run 프록시 (권장 - Google IP 사용)
 *   2. ScraperAPI (스크래핑 전문 서비스)
 *   3. Dataimpulse 레지덴셜 프록시 (TCP 소켓 직접 연결)
 *
 * Route: GET /api/check-account?username=<username>
 *
 * 환경변수 (선택 - Cloudflare Dashboard에서 설정):
 *   CLOUD_RUN_URL     - Cloud Run 서비스 URL (예: https://unfollowlens-proxy-xxx.run.app)
 *   CLOUD_RUN_API_KEY - Cloud Run 인증 키 (openssl rand -hex 32 으로 생성)
 *   SCRAPER_API_KEY   - ScraperAPI 키 (https://www.scraperapi.com)
 *   PROXY_HOST        - Dataimpulse 프록시 호스트 (예: gw.dataimpulse.com)
 *   PROXY_PORT        - Dataimpulse 프록시 포트 (예: 823)
 *   PROXY_USER        - Dataimpulse 로그인 (예: login__cr.us)
 *   PROXY_PASS        - Dataimpulse 비밀번호
 */

import { connect } from 'cloudflare:sockets';

const NO_CACHE_HEADERS = { 'Cache-Control': 'no-store, no-cache, must-revalidate' };

const FETCH_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
  Accept: 'text/html',
  'Accept-Language': 'en-US,en;q=0.9',
};

function jsonResponse(data, status = 200) {
  return Response.json(data, { status, headers: NO_CACHE_HEADERS });
}

function extractMeta(html, property) {
  const escaped = property.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = html.match(new RegExp(`<meta property="${escaped}" content="([^"]*)"`, 'i'));
  return match ? match[1] : null;
}

function decodeHtmlEntities(text) {
  return text
    .replace(/&#064;/g, '@')
    .replace(/&#x2022;/g, '\u2022')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function parseAccountFromHtml(html, username) {
  const ogImage = extractMeta(html, 'og:image');
  const ogTitle = extractMeta(html, 'og:title');
  const ogDescription = extractMeta(html, 'og:description');

  if (!ogTitle || !ogImage) {
    return {
      username,
      status: 'deleted_or_restricted',
      accessible: false,
    };
  }

  const decodedDesc = ogDescription ? decodeHtmlEntities(ogDescription) : '';

  const isPrivate =
    decodedDesc.includes('This account is private') ||
    decodedDesc.includes('This Account is Private') ||
    decodedDesc.includes('비공개 계정입니다');

  return {
    username,
    status: 'active',
    accessible: true,
    is_private: isPrivate,
    profile_pic_url: decodeHtmlEntities(ogImage),
  };
}

function hasCloudRunConfig(env) {
  return Boolean(env && env.CLOUD_RUN_URL);
}

function hasScraperApiConfig(env) {
  return Boolean(env && env.SCRAPER_API_KEY);
}

function hasProxyConfig(env) {
  return Boolean(env && env.PROXY_HOST && env.PROXY_USER && env.PROXY_PASS);
}

/**
 * Google Cloud Run 프록시를 통해 Instagram 프로필을 가져옵니다.
 *
 * Cloud Run 서버가 Google IP로 Instagram을 직접 fetch하여 HTML을 반환합니다.
 * x-api-key 헤더로 무단 접근을 차단합니다.
 *
 * @returns {{ status: number, body: string }}
 */
async function fetchViaCloudRun(username, env) {
  const url = new URL('/check-account', env.CLOUD_RUN_URL);
  url.searchParams.set('username', username);

  const headers = { Accept: 'text/html' };
  if (env.CLOUD_RUN_API_KEY) {
    headers['x-api-key'] = env.CLOUD_RUN_API_KEY;
  }

  const response = await fetch(url.toString(), { headers });
  const body = await response.text();
  return { status: response.status, body };
}

/**
 * 스크래핑 API를 통해 Instagram 프로필을 가져옵니다.
 *
 * ScraperAPI 등의 서비스를 사용하며, 표준 fetch()로 호출합니다.
 * Cloudflare Workers의 TCP 소켓 제한을 우회하는 권장 방식입니다.
 *
 * @returns {{ status: number, body: string }}
 */
async function fetchViaScrapingApi(profileUrl, env) {
  const apiUrl =
    `https://api.scraperapi.com?api_key=${env.SCRAPER_API_KEY}` +
    `&url=${encodeURIComponent(profileUrl)}&render_js=false`;

  const response = await fetch(apiUrl, {
    headers: { Accept: 'text/html' },
  });

  const body = await response.text();
  return { status: response.status, body };
}

/**
 * HTTP 포워드 프록시를 통해 Instagram 프로필을 가져옵니다.
 *
 * 흐름: connect(secureTransport:'on') → TLS로 프록시 연결 → GET (full URL) → 응답 파싱
 *
 * 참고: CONNECT 터널 + startTls() 방식은 Cloudflare Workers 프로덕션에서
 * TLS Handshake가 실패하는 알려진 제한사항이 있어, 프록시 자체에 TLS로 직접
 * 연결한 뒤 forward proxy 요청을 전송하는 방식을 사용합니다.
 * https://community.cloudflare.com/t/forward-proxy-via-cloudflare-sockets-and-starttls/862412
 *
 * @returns {{ status: number, body: string }}
 */
async function fetchViaProxy(profileUrl, env) {
  const target = new URL(profileUrl);
  const proxyPort = parseInt(env.PROXY_PORT || '823', 10);
  const auth = btoa(`${env.PROXY_USER}:${env.PROXY_PASS}`);
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  // 1. 프록시에 TLS로 직접 연결 (startTls() 우회 — 처음부터 암호화 채널 사용)
  const socket = connect(
    { hostname: env.PROXY_HOST, port: proxyPort },
    { secureTransport: 'on', allowHalfOpen: false },
  );

  // 2. TLS 채널 내에서 HTTP 포워드 프록시 요청 (프록시가 Instagram HTTPS 연결 대행)
  const httpRequest =
    `GET ${profileUrl} HTTP/1.0\r\n` +
    `Host: ${target.hostname}\r\n` +
    `Proxy-Authorization: Basic ${auth}\r\n` +
    `User-Agent: ${FETCH_HEADERS['User-Agent']}\r\n` +
    `Accept: text/html\r\n` +
    `Accept-Language: en-US,en;q=0.9\r\n` +
    `Accept-Encoding: identity\r\n` +
    `Connection: close\r\n` +
    `\r\n`;

  const writer = socket.writable.getWriter();
  await writer.write(encoder.encode(httpRequest));
  writer.releaseLock();

  // 3. 전체 응답 읽기
  const chunks = [];
  const reader = socket.readable.getReader();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    chunks.push(value);
  }

  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const fullData = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    fullData.set(chunk, offset);
    offset += chunk.length;
  }

  const responseText = decoder.decode(fullData);

  // 4. HTTP 응답 파싱 (status line + headers + body)
  const crlfIndex = responseText.indexOf('\r\n\r\n');
  const lfIndex = responseText.indexOf('\n\n');
  const headerEnd = crlfIndex !== -1 ? crlfIndex : lfIndex;
  const separatorLen = crlfIndex !== -1 ? 4 : 2;

  if (headerEnd === -1) {
    // 디버그: 프록시가 반환한 데이터 미리보기 (첫 200자 + hex)
    const preview = responseText.substring(0, 200);
    const hexBytes = Array.from(fullData.slice(0, 20))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join(' ');
    throw new Error(
      `Invalid proxy response (len=${fullData.length}, hex=[${hexBytes}], preview=${preview})`,
    );
  }

  const headerSection = responseText.substring(0, headerEnd);
  const body = responseText.substring(headerEnd + separatorLen);
  const statusLine = headerSection.split(/\r?\n/)[0];
  const statusMatch = statusLine.match(/HTTP\/[\d.]+\s+(\d+)/);
  const statusCode = statusMatch ? parseInt(statusMatch[1], 10) : 0;

  return { status: statusCode, body };
}

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const username = url.searchParams.get('username');

  if (!username || typeof username !== 'string') {
    return jsonResponse({ error: 'Missing or invalid username parameter' }, 400);
  }

  const sanitizedUsername = username.trim();

  if (sanitizedUsername.length === 0 || sanitizedUsername.length > 30) {
    return jsonResponse(
      {
        username: sanitizedUsername,
        status: 'error',
        accessible: false,
        error: 'Username must be 1-30 characters',
      },
      400,
    );
  }

  if (!/^[a-zA-Z0-9._]+$/.test(sanitizedUsername)) {
    return jsonResponse(
      {
        username: sanitizedUsername,
        status: 'error',
        accessible: false,
        error: 'Invalid username format',
      },
      400,
    );
  }

  const profileUrl = `https://www.instagram.com/${encodeURIComponent(sanitizedUsername)}/`;
  const env = context.env || {};

  try {
    // 1단계: Cloudflare IP로 직접 시도
    const response = await fetch(profileUrl, {
      headers: FETCH_HEADERS,
      redirect: 'follow',
    });

    // 2단계: 429 차단 시 fallback (Cloud Run → ScraperAPI → Dataimpulse → unknown)
    if (response.status === 429) {
      // Fallback 1: Google Cloud Run (Google IP로 Instagram fetch)
      if (hasCloudRunConfig(env)) {
        try {
          const cloudRunResult = await fetchViaCloudRun(sanitizedUsername, env);

          if (cloudRunResult.status === 404) {
            return jsonResponse({
              username: sanitizedUsername,
              status: 'deleted',
              accessible: false,
            });
          }

          if (cloudRunResult.status === 200) {
            const result = parseAccountFromHtml(cloudRunResult.body, sanitizedUsername);
            return jsonResponse(result);
          }

          // 2xx 이외 → 다음 fallback으로
        } catch {
          // Cloud Run 네트워크 에러 → 다음 fallback으로
        }
      }

      // Fallback 2: 스크래핑 API (표준 fetch()로 동작)
      if (hasScraperApiConfig(env)) {
        try {
          const apiResult = await fetchViaScrapingApi(profileUrl, env);

          if (apiResult.status === 404) {
            return jsonResponse({
              username: sanitizedUsername,
              status: 'deleted',
              accessible: false,
            });
          }

          if (apiResult.status === 200) {
            const result = parseAccountFromHtml(apiResult.body, sanitizedUsername);
            return jsonResponse(result);
          }

          // 2xx 이외 → 다음 fallback으로
        } catch {
          // 스크래핑 API 네트워크 에러 → 다음 fallback으로
        }
      }

      // Fallback 3: Dataimpulse 레지덴셜 프록시 (Cloudflare Workers TCP 제한으로 실패 가능)
      if (hasProxyConfig(env)) {
        try {
          const proxyResult = await fetchViaProxy(profileUrl, env);

          if (proxyResult.status === 404) {
            return jsonResponse({
              username: sanitizedUsername,
              status: 'deleted',
              accessible: false,
            });
          }

          if (proxyResult.status === 200) {
            const result = parseAccountFromHtml(proxyResult.body, sanitizedUsername);
            return jsonResponse(result);
          }

          return jsonResponse({
            username: sanitizedUsername,
            status: 'unknown',
            accessible: true,
            error: `HTTP ${proxyResult.status} (via proxy)`,
          });
        } catch (proxyError) {
          return jsonResponse({
            username: sanitizedUsername,
            status: 'unknown',
            accessible: true,
            error: `HTTP 429 (proxy failed: ${proxyError.message || 'unknown'})`,
          });
        }
      }

      // Fallback 없음
      return jsonResponse({
        username: sanitizedUsername,
        status: 'unknown',
        accessible: true,
        error: 'HTTP 429',
      });
    }

    if (response.status === 404) {
      return jsonResponse({
        username: sanitizedUsername,
        status: 'deleted',
        accessible: false,
      });
    }

    if (response.status !== 200) {
      return jsonResponse({
        username: sanitizedUsername,
        status: 'unknown',
        accessible: true,
        error: `HTTP ${response.status}`,
      });
    }

    const html = await response.text();
    const result = parseAccountFromHtml(html, sanitizedUsername);

    // 200이지만 og 태그가 없는 경우 (로그인 월/챌린지 페이지 가능성)
    // Cloud Run으로 재시도하여 실제 프로필 확인
    if (result.status === 'deleted_or_restricted' && hasCloudRunConfig(env)) {
      try {
        const cloudRunResult = await fetchViaCloudRun(sanitizedUsername, env);
        if (cloudRunResult.status === 200) {
          const retryResult = parseAccountFromHtml(cloudRunResult.body, sanitizedUsername);
          if (retryResult.status !== 'deleted_or_restricted') {
            return jsonResponse(retryResult);
          }
        }
        if (cloudRunResult.status === 404) {
          return jsonResponse({
            username: sanitizedUsername,
            status: 'deleted',
            accessible: false,
          });
        }
        if (cloudRunResult.status === 401) {
          return jsonResponse({
            username: sanitizedUsername,
            status: 'unknown',
            accessible: true,
            error: 'Cloud Run auth failed (API key mismatch)',
          });
        }
        if (cloudRunResult.status !== 200) {
          return jsonResponse({
            username: sanitizedUsername,
            status: 'unknown',
            accessible: true,
            error: `Cloud Run HTTP ${cloudRunResult.status}`,
          });
        }
      } catch (cloudRunError) {
        return jsonResponse({
          username: sanitizedUsername,
          status: 'unknown',
          accessible: true,
          error: `Cloud Run failed: ${cloudRunError.message || 'network error'}`,
        });
      }
    }

    return jsonResponse(result);
  } catch (error) {
    return jsonResponse({
      username: sanitizedUsername,
      status: 'error',
      accessible: true,
      error: error.message || 'Request failed',
    });
  }
}
