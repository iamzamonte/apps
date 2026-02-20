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
 *   1. Cloud Run 프록시 (Dataimpulse 레지덴셜 IP → CONNECT 터널 + 이중 TLS)
 *
 * [429 rate limit 케이스]
 *   1. ScraperAPI (스크래핑 전문 서비스)
 *   2. Cloud Run 프록시 (Dataimpulse 레지덴셜 IP → CONNECT 터널 + 이중 TLS)
 *
 * Route: GET /api/check-account?username=<username>
 *
 * 환경변수 (선택 - Cloudflare Dashboard에서 설정):
 *   SCRAPER_API_KEY   - ScraperAPI 키 (https://www.scraperapi.com)
 *   CLOUD_RUN_URL     - Cloud Run 서비스 URL (예: https://unfollowlens-proxy-xxxx.run.app)
 *   CLOUD_RUN_API_KEY - Cloud Run 인증 키
 */

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

function hasCloudRunConfig(env) {
  return Boolean(env && env.CLOUD_RUN_URL);
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
 * Cloud Run 프록시를 통해 Instagram 프로필을 가져옵니다.
 *
 * Cloud Run이 Dataimpulse 레지덴셜 프록시로 이중 TLS를 처리하고
 * 파싱 전 HTML을 그대로 반환합니다.
 *
 * @returns {{ status: number, body: string }}
 */
async function fetchViaCloudRun(profileUrl, env) {
  const username = new URL(profileUrl).pathname.split('/').filter(Boolean)[0];
  const url = new URL('/check-account', env.CLOUD_RUN_URL);
  url.searchParams.set('username', username);

  const headers = {};
  if (env.CLOUD_RUN_API_KEY) {
    headers['x-api-key'] = env.CLOUD_RUN_API_KEY;
  }

  const response = await fetch(url.toString(), {
    headers,
    signal: AbortSignal.timeout(25_000),
  });

  const body = await response.text();
  return { status: response.status, body };
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
      if (hasCloudRunConfig(env)) {
        try {
          const proxyResult = await fetchViaCloudRun(profileUrl, env);

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
            error: `HTTP 429 (cloud-run failed: ${proxyError.message || 'unknown'})`,
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
    if (result.status === 'deleted_or_restricted' && hasCloudRunConfig(env)) {
      try {
        const proxyResult = await fetchViaCloudRun(profileUrl, env);

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
