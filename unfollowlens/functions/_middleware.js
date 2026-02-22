/**
 * Cloudflare Pages Middleware
 *
 * 0. /ko → 301 / (한국어 = 루트 언어)
 * 1. ?lang=ko → 301 / | ?lang=en → 301 /en (하위 호환)
 * 2. /en, /ja 등 → index.html 서빙 (서브디렉토리 i18n)
 * 3. Preview 배포(*.pages.dev)에 X-Robots-Tag: noindex 헤더 추가
 */
const LANGS = new Set([
  'ko','en','ja','zh','es','fr','de','pt',
  'hi','ru','ar','tr','vi','th','id','ms'
]);

export async function onRequest(context) {
  const url = new URL(context.request.url);

  // 0) /ko → 301 redirect to / (Korean = root language)
  const seg = url.pathname.replace(/\/$/, '').split('/')[1];
  if (seg === 'ko') {
    url.pathname = '/';
    return Response.redirect(url.toString(), 301);
  }

  // 1) ?lang=xx → 301 redirect (ko→/, others→/xx)
  const qLang = url.searchParams.get('lang');
  if (qLang && LANGS.has(qLang)) {
    url.searchParams.delete('lang');
    url.pathname = qLang === 'ko' ? '/' : '/' + qLang;
    return Response.redirect(url.toString(), 301);
  }

  // 2) /en, /ja 등 → serve index.html
  if (seg && LANGS.has(seg)) {
    const assetUrl = new URL(url);
    assetUrl.pathname = '/index.html';
    const resp = await context.env.ASSETS.fetch(new Request(assetUrl, context.request));
    return addPreviewHeader(new Response(resp.body, resp), url);
  }

  // 3) 나머지 (/, /about, /static/*, etc.) → pass through
  const resp = await context.next();
  return addPreviewHeader(resp, url);
}

function addPreviewHeader(response, url) {
  if (url.hostname.endsWith('.pages.dev')) {
    const r = new Response(response.body, response);
    r.headers.set('X-Robots-Tag', 'noindex');
    return r;
  }
  return response;
}
