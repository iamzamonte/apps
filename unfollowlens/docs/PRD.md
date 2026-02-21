# UnfollowLens - Product Requirements Document (PRD)

## 1. 개요

### 1.1 제품명

**UnfollowLens** - 인스타그램 언팔로우 체커

### 1.2 제품 설명

UnfollowLens는 Instagram 사용자가 자신의 데이터를 업로드하여 맞팔로우하지 않는 계정(나를 팔로우하지 않는 계정)을 식별할 수 있는 무료 웹 서비스입니다.

### 1.3 목표

- 사용자가 Instagram에서 일방적으로 팔로우하는 계정을 쉽게 파악
- 개인정보 보호를 최우선으로 하는 안전한 분석 서비스 제공
- 로그인 없이 누구나 무료로 사용 가능한 접근성 확보

### 1.4 대상 사용자

- Instagram 사용자 중 팔로워/팔로잉 관리에 관심 있는 사용자
- 인플루언서, 크리에이터, 소셜 미디어 관리자
- 다국어 사용자 (16개 언어 지원: ko, en, ja, zh, es, fr, de, pt, hi, ru, ar, tr, vi, th, id, ms)

---

## 2. 기능 요구사항

### 2.1 핵심 기능

#### F1. Instagram 데이터 파일 업로드 (클라이언트 사이드)

| 항목 | 설명 |
|------|------|
| 기능 | 사용자가 Instagram에서 다운로드한 ZIP 파일 업로드 |
| 입력 | Instagram 데이터 ZIP 파일 (JSON 형식) |
| 처리 | 드래그 앤 드롭 또는 클릭하여 파일 선택 |
| 파싱 | JSZip으로 브라우저 내에서 ZIP 파일 파싱 |
| 제한 | ZIP 파일만 허용 |

#### F2. 팔로워/팔로잉 분석

| 항목 | 설명 |
|------|------|
| 기능 | 업로드된 데이터에서 팔로워와 팔로잉 목록 추출 및 비교 |
| 출력 | 맞팔하지 않는 계정 목록 (언팔로우 대상) |
| 통계 | 팔로잉 수, 팔로워 수, 맞팔 수, 언팔 대상 수 |

#### F3. 계정 상태 확인 (서버 사이드 API)

| 항목 | 설명 |
|------|------|
| 기능 | 언팔로우 대상 계정의 현재 상태 확인 |
| 방식 | Cloudflare Pages Function에서 Instagram 프로필 HTML 페이지 fetch |
| 파싱 | og:title, og:image, og:description 메타태그 파싱 |
| 분류 | 활성(active) / 삭제(deleted) / 삭제_또는_제한(deleted_or_restricted) / 미확인(unknown) |
| 비공개 | og:description에서 "This account is private" / "비공개 계정입니다" 감지 |
| 재시도 | HTTP 429 응답 시 최대 1회 재시도 (500ms 백오프) |
| 동시성 | 최대 3개 병렬 요청, 요청 간 300ms 딜레이 |

#### F4. 프로필 사진 프록시

| 항목 | 설명 |
|------|------|
| 기능 | Instagram CDN 이미지를 서버 사이드에서 프록시 |
| 목적 | 브라우저의 Referer 기반 핫링크 보호 우회 |
| 검증 | 허용된 Instagram CDN 호스트네임만 접근 가능 |
| 캐시 | CDN 레벨 7일 캐시 |
| 제한 | 이미지 크기 최대 5MB |

#### F5. 결과 표시

| 항목 | 설명 |
|------|------|
| 기능 | 분석 결과를 시각적으로 표시 |
| 섹션 | 통계 카드, 활성 계정 목록, 비활성 계정 목록 |
| 프로필 사진 | 활성 계정은 프로필 사진, 미확인 계정은 Instagram 스타일 SVG 아이콘 |
| 미확인 배지 | 서버에서 확인 실패한 계정에 "미확인" 배지 표시 |
| 액션 | 각 계정의 Instagram 프로필 바로가기 링크, 아이디 복사 버튼 |

### 2.2 부가 기능

#### F6. 다국어 지원

| 언어 | 코드 | 언어 | 코드 |
|------|------|------|------|
| 한국어 | ko | 힌디어 | hi |
| 영어 | en | 러시아어 | ru |
| 일본어 | ja | 아랍어 | ar |
| 중국어 | zh | 터키어 | tr |
| 스페인어 | es | 베트남어 | vi |
| 프랑스어 | fr | 태국어 | th |
| 독일어 | de | 인도네시아어 | id |
| 포르투갈어 | pt | 말레이어 | ms |

- **URL 방식**: 서브디렉토리 (`/ko`, `/en`, `/ja` 등)
- **하위 호환**: `?lang=ko` → 301 리다이렉트 → `/ko`
- **언어 감지 우선순위**: URL 경로 → localStorage → 브라우저 언어 → `en`
- **URL 관리**: `history.pushState`/`replaceState`로 새로고침 없이 URL 전환

#### F7. Instagram 데이터 다운로드 가이드

- 모바일 앱 가이드 (단계별 설명)
- 웹 브라우저 가이드 (단계별 설명)
- 접이식 UI로 필요시 펼쳐보기

#### F8. FAQ 섹션

| 항목 | 설명 |
|------|------|
| 기능 | 자주 묻는 질문 6개를 아코디언 토글로 표시 |
| UI | 한 번에 하나의 질문만 펼쳐지는 아코디언 패턴 |
| 다국어 | 16개 언어 번역 지원 (`data-i18n` 속성) |
| SEO | FAQPage JSON-LD 구조화 데이터 |
| 질문 | 서비스 안전성, 데이터 다운로드 시간, 언팔로워 정의, 비용/제한, 결과 차이, 개인정보 보호 |

#### F9. 대용량 데이터 분석 제한

| 항목 | 설명 |
|------|------|
| 기능 | 팔로잉+팔로워 합계 100만 건 초과 시 분석 차단 |
| 시점 | ZIP 파싱 완료 후, 계정 상태 확인 API 호출 전 |
| UI | 다국어 안내 팝업 (모달) |
| 대응 | 분석 중단, 로딩 숨김, 버튼 재활성화 |

---

## 3. 비기능 요구사항

### 3.1 성능

| 항목 | 요구사항 |
|------|----------|
| 파일 파싱 | 브라우저 내에서 즉시 처리 (서버 업로드 없음) |
| 계정 확인 | 병렬 3개 요청, 요청 간 300ms 딜레이 |

### 3.2 보안 및 개인정보

| 항목 | 요구사항 |
|------|----------|
| 데이터 처리 | 모든 ZIP 파싱이 브라우저 내에서 수행 |
| 서버 저장 | 없음 - 서버는 계정 상태 확인 API만 제공 |
| 전송 암호화 | HTTPS 필수 |
| 로그인 | 불필요 (익명 사용) |
| 이미지 프록시 | 허용된 Instagram CDN 도메인만 접근 가능 |

### 3.3 접근성

| 항목 | 요구사항 |
|------|----------|
| 반응형 | 모바일, 태블릿, 데스크톱 지원 |
| 브라우저 | Chrome, Safari, Firefox, Edge 최신 버전 |

### 3.4 SEO

| 항목 | 요구사항 |
|------|----------|
| 메타 태그 | Open Graph, Twitter Card 지원 |
| 다국어 SEO | hreflang 태그 (16개 언어 + x-default, 서브디렉토리 URL) |
| 사이트맵 | XML sitemap (16개 언어별 URL + hreflang 상호 참조) |
| 로봇 | robots.txt 제공 |
| 검색 엔진 인증 | Google, Naver, Bing 사이트 인증 |
| 구조화 데이터 | WebApplication + FAQPage JSON-LD |
| i18n URL | 서브디렉토리 방식 (`/ko`, `/en`) |

---

## 4. 기술 스택

### 4.1 프론트엔드

| 항목 | 기술 |
|------|------|
| HTML/CSS/JS | Vanilla (프레임워크 없음, 단일 SPA 파일) |
| ZIP 파싱 | JSZip (CDN) |
| 스타일링 | 인라인 CSS |

### 4.2 백엔드

| 항목 | 기술 |
|------|------|
| 런타임 | Cloudflare Pages Functions |
| 미들웨어 | `_middleware.js` — i18n URL 라우팅, `?lang=` 301 리다이렉트, preview noindex |
| API | check-account.js, proxy-image.js |

### 4.3 인프라

| 항목 | 기술 |
|------|------|
| 호스팅 | Cloudflare Pages |
| 도메인 | unfollowlens.com |
| CDN | Cloudflare (자동) |

### 4.4 개발 도구

| 항목 | 기술 |
|------|------|
| 테스트 | Vitest |
| 린트 | ESLint 9 + eslint-config-prettier |
| 포맷 | Prettier |
| 로컬 개발 | Wrangler Pages Dev |

---

## 5. 데이터 흐름

```
┌─────────────────────────────────────────────────┐
│                 사용자 브라우저                      │
│                                                   │
│  1. ZIP 파일 선택 (드래그 앤 드롭)                   │
│  2. JSZip으로 브라우저 내 파싱                       │
│  3. followers.json / following.json 추출            │
│  4. 팔로워/팔로잉 비교 → 언팔 대상 추출               │
│  5. 결과 표시 (통계 카드 + 계정 목록)                 │
└─────────────────┬───────────────────────────────┘
                  │
                  │ 6. 계정별 상태 확인 요청 (병렬 3개)
                  ▼
┌─────────────────────────────────────────────────┐
│          Cloudflare Pages Functions               │
│                                                   │
│  /api/check-account?username=<username>           │
│  ├── Instagram 프로필 HTML fetch (Googlebot UA)    │
│  ├── og:* 메타태그 파싱                            │
│  ├── 429 재시도 (1회, 500ms 백오프)                │
│  └── 상태 반환 (active/deleted/unknown 등)         │
│                                                   │
│  /api/proxy-image?url=<cdn_url>                   │
│  ├── Instagram CDN 이미지 fetch                    │
│  ├── 호스트네임 허용 목록 검증                      │
│  └── 이미지 바이너리 반환                           │
└─────────────────────────────────────────────────┘
```

---

## 6. API 명세

### 6.1 GET /api/check-account

Instagram 계정 상태 확인

**Request**: `?username=<username>`

**Response (활성 계정)**:
```json
{
  "username": "instagram",
  "status": "active",
  "accessible": true,
  "is_private": false,
  "profile_pic_url": "https://cdn.instagram.com/..."
}
```

**Response (삭제된 계정)**:
```json
{
  "username": "deleted_user",
  "status": "deleted",
  "accessible": false
}
```

**Response (에러)**:
```json
{
  "error": "Missing or invalid username parameter"
}
```

### 6.2 GET /api/proxy-image

Instagram CDN 이미지 프록시

**Request**: `?url=<encoded_url>`

**Response**: 이미지 바이너리 + Cache-Control: public, max-age=86400

---

## 7. 알려진 제한사항 및 대응

### 7.1 Instagram 429 Rate Limit

| 문제 | 설명 |
|------|------|
| 현상 | Cloudflare 데이터센터 IP에서 Instagram 프로필 접근 시 HTTP 429 반환 |
| 원인 | Instagram이 데이터센터 IP 대역을 차단 (Rate Limit이 아닌 IP 블록) |
| 영향 | 운영 환경에서 계정 상태 확인 실패 → 모든 계정이 "미확인"으로 표시 |
| 대응 | 미확인 배지 + Instagram 프로필 직접 링크 제공 |

### 7.2 CORS 제한

브라우저에서 직접 Instagram 프로필을 fetch할 수 없음 (CORS, CORB, Same-Origin Policy). 반드시 서버 사이드 프록시가 필요.

### 7.3 무료 프록시 서비스 제한

allorigins.win, corsproxy.io 등 무료 CORS 프록시도 데이터센터 IP를 사용하므로 Instagram에 의해 차단됨.

---

## 8. 수익화

### 8.1 광고

| 플랫폼 | 상태 |
|--------|------|
| Google AdSense | 연동 완료 |

### 8.2 후원

| 플랫폼 | 링크 |
|--------|------|
| Buy Me a Coffee | buymeacoffee.com/zamonte |
| Ko-fi | ko-fi.com/montecarlo62602 |

---

## 9. 로드맵

### Phase 1 (완료)

- [x] 핵심 기능 개발 (업로드, 분석, 결과 표시)
- [x] 다국어 지원 (5개 언어)
- [x] 반응형 UI
- [x] Cloudflare Pages 배포

### Phase 2 (완료)

- [x] SEO 최적화 (OG, hreflang, sitemap)
- [x] Google AdSense 연동
- [x] 계정 상태 확인 API (check-account)
- [x] 프로필 사진 프록시 API (proxy-image)
- [x] 429 재시도 로직
- [x] 미확인 계정 배지 표시
- [x] 비공개 계정 감지

### Phase 3 (완료)

- [x] 16개 언어 확장 (ko, en, ja, zh, es, fr, de, pt, hi, ru, ar, tr, vi, th, id, ms)
- [x] 서브디렉토리 i18n URL (`/ko`, `/en`) + `?lang=` 301 리다이렉트
- [x] Cloudflare Pages 미들웨어 URL 라우팅
- [x] FAQ 섹션 (7개 질문, 아코디언 토글, FAQPage JSON-LD)
- [x] 100만 건 분석 제한 + 다국어 안내 팝업
- [x] 언어 선택기 UI 개선 (상단 우측 드롭다운)
- [x] hreflang 16개 언어 서브디렉토리 URL
- [x] sitemap.xml 16개 언어별 URL 엔트리

### Phase 4 (예정)

- [ ] 결과 내보내기 (CSV/Excel)
- [ ] 다크 모드
- [ ] PWA 지원
- [ ] 블로그/가이드 콘텐츠

---

## 10. 리스크 및 고려사항

### 10.1 기술적 리스크

| 리스크 | 완화 방안 |
|--------|----------|
| Instagram 데이터 형식 변경 | 다양한 형식 지원, 에러 핸들링 강화 |
| Instagram 프로필 접근 차단 (429) | 미확인 배지 + 직접 프로필 링크 제공 |
| Instagram CDN 이미지 접근 차단 | proxy-image API로 서버 사이드 프록시 |

### 10.2 법적 리스크

| 리스크 | 완화 방안 |
|--------|----------|
| Instagram 이용약관 | 공개 정보만 접근, 로그인 불필요 |
| 개인정보 보호법 | 데이터 미저장 (브라우저 내 처리), 투명한 처리방침 |

---

**문서 버전**: 3.0
**최종 업데이트**: 2026년 2월
