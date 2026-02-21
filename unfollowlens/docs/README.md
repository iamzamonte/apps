# UnfollowLens

Instagram에서 나를 팔로우하지 않는 계정을 찾아주는 웹 애플리케이션입니다.

## Live Demo

**https://unfollowlens.com/**

## 주요 기능

- Instagram 데이터 ZIP 파일 분석 (클라이언트 사이드)
- 맞팔하지 않는 계정 탐지
- 계정 상태 확인 (활성/탈퇴/제한/비공개)
- 탈퇴/제한된 계정 자동 필터링
- 프로필 사진 표시 (이미지 프록시)
- 미확인 계정 표시 (서버 확인 실패 시)
- 다국어 지원 (16개 언어, 서브디렉토리 URL: `/ko`, `/en`, `/ja` 등)
- FAQ 섹션 (아코디언 토글, 7개 질문, FAQPage JSON-LD)
- 대용량 데이터 분석 제한 (팔로잉+팔로워 100만 건 초과 시 안내 팝업)
- 개인정보 보호 (모든 처리가 브라우저에서 수행, 서버 저장 없음)

## 기술 스택

| 분류 | 기술 |
|------|------|
| Frontend | HTML, CSS, JavaScript (Vanilla) |
| Backend | Cloudflare Pages Functions |
| Testing | Vitest |
| Linting | ESLint + Prettier |
| Deployment | Cloudflare Pages |
| Domain | unfollowlens.com |

## 아키텍처

```
사용자 브라우저
├── dist/index.html (SPA)
│   ├── ZIP 파일 파싱 (JSZip)
│   ├── 팔로워/팔로잉 비교 (100만 건 제한 체크)
│   ├── 결과 렌더링
│   └── 서브디렉토리 i18n (pushState/replaceState)
│
├── functions/_middleware.js (Cloudflare Pages 미들웨어)
│   ├── /ko, /en 등 → index.html 서빙 (i18n URL 라우팅)
│   ├── ?lang=ko → 301 /ko (하위 호환 리다이렉트)
│   └── *.pages.dev → X-Robots-Tag: noindex (preview 차단)
│
├── /api/check-account?username=<username>
│   └── functions/api/check-account.js
│       ├── Instagram 프로필 HTML 페이지 fetch
│       ├── og:* 메타태그 파싱
│       ├── 429 Rate Limit 재시도 (최대 1회)
│       └── 계정 상태 판별 (active/deleted/deleted_or_restricted/unknown)
│
└── /api/proxy-image?url=<instagram_cdn_url>
    └── functions/api/proxy-image.js
        ├── Instagram CDN 이미지 프록시
        ├── 허용 호스트네임 검증
        └── 이미지 크기 제한 (5MB)
```

## 로컬 개발

### 요구사항

- Node.js 18+
- npm

### 설치

```bash
cd instagram/unfollowlens
npm install
```

### 실행

```bash
# 로컬 개발 서버 (Wrangler Pages Dev)
npm run dev

# 브라우저에서 http://localhost:8788 접속
```

### 테스트

```bash
# 테스트 실행
npm test

# 테스트 watch 모드
npm run test:watch

# 린트 + 포맷 + 테스트
npm run ci
```

## Instagram 데이터 다운로드 방법

1. Instagram 앱/웹에서 **설정** → **계정 센터** → **내 정보 및 권한**
2. **내 정보 다운로드** 선택
3. **일부 정보 다운로드** → **팔로워 및 팔로잉** 선택
4. 형식: **JSON**, 기간: **전체 기간**
5. 이메일로 받은 ZIP 파일 업로드

## 프로젝트 구조

```
unfollowlens/
├── dist/
│   ├── index.html              # SPA (HTML + CSS + JS 단일 파일)
│   ├── sitemap.xml             # 16개 언어 hreflang 사이트맵
│   ├── robots.txt              # 크롤러 설정
│   ├── ads.txt                 # AdSense 퍼블리셔 인증
│   ├── _headers                # Cache-Control 설정
│   └── static/og-image.png     # 소셜 공유 이미지 (1200x630)
├── functions/
│   ├── _middleware.js           # i18n URL 라우팅 + preview noindex
│   └── api/
│       ├── check-account.js    # 계정 상태 확인 API
│       └── proxy-image.js      # Instagram CDN 이미지 프록시
├── docs/
│   ├── README.md               # 프로젝트 소개
│   ├── PRD.md                  # 제품 요구사항 문서
│   ├── seo-guide.md            # SEO 설정 가이드
│   ├── monitoring-guide.md     # 모니터링 가이드
│   └── instagram-cloud-ip-blocking.md  # IP 차단 대응
├── tests/
│   ├── check-account.test.js   # check-account API 테스트 (23개)
│   └── proxy-image.test.js     # proxy-image API 테스트
├── wrangler.jsonc               # Cloudflare Pages 설정
├── vitest.config.js             # Vitest 설정
├── eslint.config.js             # ESLint 설정
└── package.json
```

## API 명세

### GET /api/check-account

Instagram 계정 상태를 확인합니다.

**Request**: `?username=<instagram_username>`

**Response**:
```json
{
  "username": "instagram",
  "status": "active",
  "accessible": true,
  "is_private": false,
  "profile_pic_url": "https://cdn.instagram.com/..."
}
```

**status 값**:
| status | 설명 |
|--------|------|
| `active` | 활성 계정 |
| `deleted` | 삭제된 계정 (404) |
| `deleted_or_restricted` | 삭제/제한 계정 (og 태그 없음) |
| `unknown` | 확인 불가 (429 등) |
| `error` | 네트워크 오류 |

### GET /api/proxy-image

Instagram CDN 이미지를 프록시합니다.

**Request**: `?url=<encoded_instagram_cdn_url>`

**Response**: 이미지 바이너리 (Content-Type: image/*)

## 알려진 제한사항

- Instagram은 Cloudflare 데이터센터 IP에서의 접근을 차단(HTTP 429)하여, 운영 환경에서 계정 상태 확인이 실패할 수 있음
- 확인 실패 시 "미확인" 배지와 함께 프로필 링크를 제공하여 사용자가 직접 확인 가능
- 팔로잉+팔로워 합계 100만 건 초과 시 브라우저 내 분석이 제한됨 (안내 팝업 표시)

## 문서

- [PRD.md](./PRD.md) - 제품 요구사항 문서
- [seo-guide.md](./seo-guide.md) - SEO 설정 가이드
- [monitoring-guide.md](./monitoring-guide.md) - 모니터링 및 트러블슈팅 가이드
- [instagram-cloud-ip-blocking.md](./instagram-cloud-ip-blocking.md) - Instagram 클라우드 IP 차단 대응

## 후원

이 프로젝트가 유용하셨다면 커피 한 잔 사주세요!

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/zamonte)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/montecarlo62602)

## 라이선스

MIT License
