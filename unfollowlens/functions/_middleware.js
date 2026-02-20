/**
 * Cloudflare Pages Middleware
 *
 * Preview 배포(*.pages.dev)에 X-Robots-Tag: noindex 헤더를 추가하여
 * 검색엔진이 preview URL을 인덱싱하는 것을 방지합니다.
 *
 * Production 배포(unfollowlens.com)에는 영향 없음.
 */
export async function onRequest(context) {
  const response = await context.next();
  const url = new URL(context.request.url);

  if (url.hostname.endsWith('.pages.dev')) {
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('X-Robots-Tag', 'noindex');
    return newResponse;
  }

  return response;
}
