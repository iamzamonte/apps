/**
 * Cloudflare Pages Function - Instagram 계정 상태 확인
 *
 * Instagram 프로필 HTML 페이지의 og:* 메타태그를 파싱하여
 * 계정 상태와 프로필 사진을 가져옵니다.
 *
 * Instagram이 클라우드 IP를 감지하여 로그인 페이지를 반환하는 경우
 * 아래 순서로 레지덴셜 IP fallback을 시도합니다:
 *
 * [200 로그인 월 케이스]
 *   1. Dataimpulse 레지덴셜 프록시 (CONNECT 터널 → inner TLS)
 *
 * [429 rate limit 케이스]
 *   1. ScraperAPI (스크래핑 전문 서비스)
 *   2. Dataimpulse 레지덴셜 프록시 (CONNECT 터널 → inner TLS)
 *
 * Route: GET /api/check-account?username=<username>
 *
 * 환경변수 (선택 - Cloudflare Dashboard에서 설정):
 *   SCRAPER_API_KEY - ScraperAPI 키 (https://www.scraperapi.com)
 *   PROXY_HOST      - Dataimpulse 프록시 호스트 (예: gw.dataimpulse.com)
 *   PROXY_PORT      - Dataimpulse 프록시 포트 (예: 823)
 *   PROXY_USER      - Dataimpulse 로그인 (예: login__cr.us)
 *   PROXY_PASS      - Dataimpulse 비밀번호
 */

import tls from 'node:tls';

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

function hasScraperApiConfig(env) {
  return Boolean(env && env.SCRAPER_API_KEY);
}

function hasProxyConfig(env) {
  return Boolean(env && env.PROXY_HOST && env.PROXY_USER && env.PROXY_PASS);
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
 * CONNECT 터널을 통해 Instagram 프로필을 가져옵니다.
 *
 * 흐름 (node:tls 이중 TLS):
 *   tls.connect(proxy:823) [outer TLS]
 *   → CONNECT instagram.com:443 → 200 OK
 *   → tls.connect({ socket: outerSocket }) [inner TLS]
 *   → GET /path/ HTTP/1.0 → 응답 파싱
 *
 * cloudflare:sockets의 startTls() 이중 호출 제한을 node:tls로 우회합니다.
 * (nodejs_compat 플래그 필요)
 *
 * @returns {{ status: number, body: string }}
 */
async function fetchViaProxy(profileUrl, env) {
  const target = new URL(profileUrl);
  const proxyPort = parseInt(env.PROXY_PORT || '823', 10);
  const auth = btoa(`${env.PROXY_USER}:${env.PROXY_PASS}`);

  // 1. 프록시에 outer TLS 연결 (포트 823 = HTTPS proxy)
  const outerSocket = await new Promise((resolve, reject) => {
    const s = tls.connect(
      { host: env.PROXY_HOST, port: proxyPort, rejectUnauthorized: false },
      () => resolve(s),
    );
    s.on('error', (e) => reject(new Error(`Proxy TLS error: ${e.message}`)));
    s.setTimeout(15000, () => {
      s.destroy();
      reject(new Error('Proxy connection timeout'));
    });
  });

  // 2. CONNECT 터널 요청 후 200 OK 대기
  await new Promise((resolve, reject) => {
    const connectReq =
      `CONNECT ${target.hostname}:443 HTTP/1.0\r\n` +
      `Host: ${target.hostname}:443\r\n` +
      `Proxy-Authorization: Basic ${auth}\r\n` +
      `\r\n`;

    outerSocket.write(connectReq, 'utf8');

    let buf = '';
    const onData = (chunk) => {
      buf += chunk.toString('utf8');
      if (buf.includes('\r\n\r\n') || buf.includes('\n\n')) {
        outerSocket.removeListener('data', onData);
        const statusLine = buf.split(/\r?\n/)[0];
        const match = statusLine.match(/HTTP\/[\d.]+\s+(\d+)/);
        const code = match ? parseInt(match[1], 10) : 0;
        if (code === 200) resolve();
        else reject(new Error(`CONNECT failed: ${statusLine.trim()}`));
      }
    };
    outerSocket.on('data', onData);
    outerSocket.once('error', (e) => reject(new Error(`CONNECT error: ${e.message}`)));
  });

  // 3. inner TLS 핸드셰이크 (instagram.com, 터널 위에서)
  const innerSocket = await new Promise((resolve, reject) => {
    const s = tls.connect(
      { socket: outerSocket, host: target.hostname, rejectUnauthorized: false },
      () => resolve(s),
    );
    s.on('error', (e) => reject(new Error(`Instagram TLS error: ${e.message}`)));
  });

  // 4. HTTP GET 요청 전송 (inner TLS 위에서, path 기반)
  const httpRequest =
    `GET ${target.pathname} HTTP/1.0\r\n` +
    `Host: ${target.hostname}\r\n` +
    `User-Agent: ${FETCH_HEADERS['User-Agent']}\r\n` +
    `Accept: text/html\r\n` +
    `Accept-Language: en-US,en;q=0.9\r\n` +
    `Accept-Encoding: identity\r\n` +
    `Connection: close\r\n` +
    `\r\n`;

  await new Promise((resolve, reject) => {
    innerSocket.write(httpRequest, 'utf8', (err) => (err ? reject(err) : resolve()));
  });

  // 5. 전체 응답 수집
  const fullData = await new Promise((resolve, reject) => {
    const chunks = [];
    innerSocket.on('data', (chunk) => chunks.push(chunk));
    innerSocket.on('end', () => resolve(Buffer.concat(chunks)));
    innerSocket.on('error', reject);
  });
  innerSocket.destroy();

  // 6. HTTP 응답 파싱 (status line + headers + body)
  const responseText = fullData.toString('utf8');
  const crlfIndex = responseText.indexOf('\r\n\r\n');
  const lfIndex = responseText.indexOf('\n\n');
  const headerEnd = crlfIndex !== -1 ? crlfIndex : lfIndex;
  const separatorLen = crlfIndex !== -1 ? 4 : 2;

  if (headerEnd === -1) {
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

    // 2단계: 429 rate limit 시 fallback (ScraperAPI → Dataimpulse → unknown)
    if (response.status === 429) {
      // Fallback 1: ScraperAPI (표준 fetch()로 동작)
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
          // ScraperAPI 네트워크 에러 → 다음 fallback으로
        }
      }

      // Fallback 2: Dataimpulse 레지덴셜 프록시
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

    // 200이지만 og 태그가 없는 경우 = Instagram이 클라우드 IP에 로그인 월 반환
    // Dataimpulse 레지덴셜 프록시로 재시도하여 실제 프로필 확인
    if (result.status === 'deleted_or_restricted' && hasProxyConfig(env)) {
      try {
        const proxyResult = await fetchViaProxy(profileUrl, env);

        if (proxyResult.status === 200) {
          const retryResult = parseAccountFromHtml(proxyResult.body, sanitizedUsername);
          return jsonResponse(retryResult);
        }

        if (proxyResult.status === 404) {
          return jsonResponse({
            username: sanitizedUsername,
            status: 'deleted',
            accessible: false,
          });
        }
      } catch {
        // Dataimpulse 실패 → 원래 deleted_or_restricted 반환
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
