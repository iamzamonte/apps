/**
 * Cloudflare Pages Function - Instagram Image Proxy
 *
 * Instagram CDN 이미지를 서버 사이드에서 가져와 클라이언트에 전달합니다.
 * 브라우저의 Referer 기반 핫링크 보호를 우회합니다.
 *
 * Route: GET /api/proxy-image?url=<encoded_instagram_cdn_url>
 */

const ALLOWED_HOSTNAME_PATTERNS = [
  /^.*\.cdninstagram\.com$/,
  /^.*\.fbcdn\.net$/,
  /^.*\.instagram\.com$/,
];

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;

const CACHE_HEADERS = {
  'Cache-Control': 'public, max-age=86400, s-maxage=604800',
};

function isAllowedUrl(urlString) {
  try {
    const parsed = new URL(urlString);
    if (parsed.protocol !== 'https:') {
      return false;
    }
    return ALLOWED_HOSTNAME_PATTERNS.some((pattern) => pattern.test(parsed.hostname));
  } catch {
    return false;
  }
}

function errorResponse(message, status = 400) {
  return Response.json({ error: message }, { status, headers: { 'Cache-Control': 'no-store' } });
}

export async function onRequestGet(context) {
  const requestUrl = new URL(context.request.url);
  const imageUrl = requestUrl.searchParams.get('url');

  if (!imageUrl) {
    return errorResponse('Missing url parameter');
  }

  if (!isAllowedUrl(imageUrl)) {
    return errorResponse('URL not allowed: must be an Instagram CDN URL');
  }

  try {
    const response = await fetch(imageUrl, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        Accept: 'image/*',
      },
      redirect: 'follow',
    });

    if (!response.ok) {
      return errorResponse(`Upstream returned HTTP ${response.status}`, 502);
    }

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.startsWith('image/')) {
      return errorResponse('Upstream did not return an image', 502);
    }

    const contentLength = response.headers.get('content-length');
    if (contentLength && parseInt(contentLength, 10) > MAX_IMAGE_SIZE) {
      return errorResponse('Image too large', 502);
    }

    const imageBody = await response.arrayBuffer();

    if (imageBody.byteLength > MAX_IMAGE_SIZE) {
      return errorResponse('Image too large', 502);
    }

    return new Response(imageBody, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Content-Length': String(imageBody.byteLength),
        ...CACHE_HEADERS,
      },
    });
  } catch (error) {
    return errorResponse(error.message || 'Failed to fetch image', 502);
  }
}
