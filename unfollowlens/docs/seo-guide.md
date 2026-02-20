# Unfollowlens SEO 가이드

> 최종 수정: 2026-02-21

## 1. 현재 SEO 설정 현황

### 검색엔진 인증

| 검색엔진 | 메타태그 | 파일 |
|----------|---------|------|
| Google | `google-site-verification` | `dist/index.html` |
| Naver | `naver-site-verification` (2개) | `dist/index.html` |
| Bing | `msvalidate.01` | `dist/index.html` |

### 관리 콘솔 URL

| 서비스 | URL |
|--------|-----|
| Google Search Console | https://search.google.com/search-console |
| Naver Search Advisor | https://webmaster.naver.com |
| Bing Webmaster Tools | https://www.bing.com/webmasters |

### 메타태그 구성 (`dist/index.html`)

```html
<!-- 기본 SEO -->
<meta name="description" content="인스타그램 맞팔 확인, 언팔 대상 찾기...">
<meta name="keywords" content="인스타그램, 언팔, 맞팔, 팔로워 분석, Instagram unfollow">
<meta name="author" content="UnfollowLens">
<meta name="robots" content="index, follow">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:url" content="https://unfollowlens.com">
<meta property="og:title" content="UnfollowLens - 인스타그램 언팔 체커">
<meta property="og:description" content="나를 팔로우하지 않는 계정을 찾아보세요.">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="https://unfollowlens.com/static/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="UnfollowLens - 인스타그램 언팔 체커">
<meta name="twitter:description" content="나를 팔로우하지 않는 계정을 찾아보세요.">
<meta name="twitter:image" content="https://unfollowlens.com/static/og-image.png">

<!-- Canonical & 다국어 -->
<link rel="canonical" href="https://unfollowlens.com">
<link rel="alternate" hreflang="ko" href="https://unfollowlens.com?lang=ko">
<link rel="alternate" hreflang="en" href="https://unfollowlens.com?lang=en">
<link rel="alternate" hreflang="ja" href="https://unfollowlens.com?lang=ja">
<link rel="alternate" hreflang="zh" href="https://unfollowlens.com?lang=zh">
<link rel="alternate" hreflang="es" href="https://unfollowlens.com?lang=es">
```

### 구조화 데이터 (JSON-LD)

`dist/index.html` 하단에 `WebApplication` 스키마:

```json
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "UnfollowLens",
  "url": "https://unfollowlens.com",
  "description": "인스타그램 맞팔 확인, 언팔 대상 찾기...",
  "applicationCategory": "SocialNetworkingApplication",
  "operatingSystem": "Any",
  "browserRequirements": "Requires JavaScript",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "KRW"
  },
  "author": {
    "@type": "Organization",
    "name": "UnfollowLens"
  }
}
```

### 정적 파일

| 파일 | 위치 | 용도 |
|------|------|------|
| `sitemap.xml` | `dist/sitemap.xml` | 검색엔진 크롤링용 사이트맵 (5개 언어 hreflang 포함) |
| `robots.txt` | `dist/robots.txt` | 크롤러 접근 허용 + 사이트맵 참조 |
| `ads.txt` | `dist/ads.txt` | AdSense 퍼블리셔 인증 |
| `og-image.png` | `dist/static/og-image.png` | 소셜 공유 미리보기 이미지 (1200x630) |

### 페이지별 SEO

| 페이지 | 경로 | canonical | robots |
|--------|------|-----------|--------|
| 메인 | `/` | `https://unfollowlens.com` | index, follow |
| 서비스 소개 | `/about` | `https://unfollowlens.com/about` | index, follow |
| 개인정보 처리방침 | `/privacy` | `https://unfollowlens.com/privacy` | index, follow |
| 이용약관 | `/terms` | `https://unfollowlens.com/terms` | index, follow |

## 2. Google Analytics 4

### 설정 정보

- **측정 ID**: `G-B2PVMKTZF4`
- **적용 파일**: `dist/index.html`, `dist/about/index.html`, `dist/privacy/index.html`, `dist/terms/index.html`
- **대시보드**: https://analytics.google.com/

### 추적 코드 위치

각 HTML 파일의 `<head>` 상단 (`<meta charset>` → `<meta viewport>` 바로 다음):

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-B2PVMKTZF4"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-B2PVMKTZF4');
</script>
```

### GA4 주요 확인 항목

- **실시간 보고서**: 현재 활성 사용자 확인
- **획득(Acquisition)**: 검색엔진별 유입 채널 (Organic Search, Direct, Referral)
- **참여(Engagement)**: 페이지별 조회수, 체류 시간
- **이벤트**: 자동 수집 이벤트 (page_view, scroll, click 등)

## 3. Preview 배포 noindex 설정

### 문제

Cloudflare Pages는 production 외에 `*.unfollowlens.pages.dev` preview URL도 생성.
검색엔진이 preview URL을 인덱싱하면 중복 콘텐츠 문제 발생.

### 해결

`functions/_middleware.js`에서 hostname 기반으로 조건부 `X-Robots-Tag` 헤더 추가:

```javascript
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
```

### 동작

```
요청 → _middleware.js
  ├─ unfollowlens.com      → 그대로 통과 (인덱싱 허용)
  └─ *.pages.dev            → X-Robots-Tag: noindex (인덱싱 차단)
```

### 검증

```bash
# Preview → noindex 헤더 있어야 함
curl -sI https://<preview-hash>.unfollowlens.pages.dev/ | grep -i x-robots

# Production → noindex 헤더 없어야 함
curl -sI https://unfollowlens.com/ | grep -i x-robots
```

## 4. AdSense

### 설정 정보

- **퍼블리셔 ID**: `ca-pub-4674053917795285`
- **ads.txt**: `dist/ads.txt`에 등록

```
google.com, pub-4674053917795285, DIRECT, f08c47fec0942fa0
```

### 적용 위치

모든 HTML 파일 `<head>`에:

```html
<meta name="google-adsense-account" content="ca-pub-4674053917795285">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4674053917795285" crossorigin="anonymous"></script>
```

## 5. 검색엔진 유입 흐름

```
사용자 키워드 검색
  │
  ├─ Google: "인스타그램 언팔 확인", "instagram unfollow checker"
  ├─ Naver:  "인스타 맞팔 확인", "언팔 체커"
  ├─ Bing:   "instagram unfollow tracker"
  └─ Daum:   "인스타 팔로워 분석"
  │
  ▼
검색엔진 크롤러 → 사이트 발견
  │
  ├─ robots.txt 확인 → 크롤링 허용
  ├─ sitemap.xml 파싱 → 모든 페이지 URL 수집
  ├─ HTML 렌더링 → meta 태그 + JSON-LD 파싱
  └─ 인덱싱 → 검색 결과에 등록
  │
  ▼
검색 결과 노출
  │
  ├─ 제목: og:title → "UnfollowLens - 인스타그램 언팔 체커"
  ├─ 설명: description → "나를 팔로우하지 않는 계정을 찾아보세요."
  └─ 이미지: og:image (소셜 공유 시)
  │
  ▼
사용자 클릭 → unfollowlens.com 방문 → GA4 추적
```

## 6. 검색엔진 등록 및 사이트맵 제출

### Google Search Console

1. https://search.google.com/search-console 접속
2. 속성 선택 (unfollowlens.com) — `google-site-verification` 메타태그로 인증 완료
3. **Sitemaps** 메뉴 → `https://unfollowlens.com/sitemap.xml` 제출
4. **Performance** 탭에서 검색 쿼리, 클릭수, 노출수 모니터링
5. **Pages** 탭에서 인덱싱 상태 및 오류 확인

### Naver Search Advisor

1. https://webmaster.naver.com 접속
2. 사이트 선택 (unfollowlens.com) — `naver-site-verification` 메타태그로 인증 완료
3. **요청 → 사이트맵 제출** → `https://unfollowlens.com/sitemap.xml`
4. **요청 → 웹 페이지 수집** → 주요 URL 수동 제출

> Naver의 Yeti 봇은 사이트맵 없이 깊이 크롤링하지 않으므로 사이트맵 제출 필수

### Bing Webmaster Tools

1. https://www.bing.com/webmasters 접속
2. Google Search Console에서 자동 가져오기 가능 (Import from GSC)
3. 또는 `msvalidate.01` 메타태그로 수동 인증
4. 사이트맵 제출

## 7. 수익화 옵션

### 현재 적용됨

- **Google AdSense**: 자동 광고 (퍼블리셔 ID 등록 완료)

### 추가 가능 옵션

| 방법 | 특징 | 적합 트래픽 |
|------|------|------------|
| Ko-fi / Buy Me a Coffee | 기부 기반, 즉시 설정, 수수료 0-5% | 모든 트래픽 |
| 프리미엄 모델 | 무료 기본 기능 + 유료 고급 기능 | 1,000+/월 |
| 카카오 애드핏 | 한국 광고 네트워크, 웹앱 지원 | 1,000+/월 |
| 제휴 마케팅 | 관련 서비스 추천 링크 | 5,000+/월 |

### 카카오 애드핏 연동 방법

공식 문서: https://adfit.github.io/wiki/web-guide/

1. AdFit 계정 가입
2. **광고 관리** 메뉴에서 미디어 등록
3. 광고 단위 생성 (320x100, 300x250, 728x90 등)
4. SDK 스크립트 설치
5. 심사 통과 후 광고 노출

## 8. SEO 체크리스트

### 파일 구성

- [x] `dist/index.html` — 메타태그, OG, Twitter Card, JSON-LD, GA4, AdSense
- [x] `dist/about/index.html` — 메타태그, canonical, GA4, AdSense
- [x] `dist/privacy/index.html` — 메타태그, canonical, GA4, AdSense
- [x] `dist/terms/index.html` — 메타태그, canonical, GA4, AdSense
- [x] `dist/sitemap.xml` — 다국어 hreflang, lastmod, priority
- [x] `dist/robots.txt` — Allow: /, Sitemap 참조
- [x] `dist/ads.txt` — AdSense 퍼블리셔 인증
- [x] `dist/static/og-image.png` — 1200x630 소셜 공유 이미지
- [x] `functions/_middleware.js` — Preview 배포 noindex

### 검색엔진 인증

- [x] Google Search Console — `google-site-verification`
- [x] Naver Search Advisor — `naver-site-verification`
- [x] Bing Webmaster Tools — `msvalidate.01`

### 트래킹

- [x] Google Analytics 4 — `G-B2PVMKTZF4`
- [x] Google AdSense — `ca-pub-4674053917795285`

### 운영 확인 사항

- [ ] Google Search Console에 사이트맵 제출 확인
- [ ] Naver Search Advisor에 사이트맵 제출 확인
- [ ] Bing Webmaster Tools에 사이트맵 제출 확인
- [ ] GA4 실시간 보고서에서 데이터 수신 확인
- [ ] AdSense 승인 상태 확인
