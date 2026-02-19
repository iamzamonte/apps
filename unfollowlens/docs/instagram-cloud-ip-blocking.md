# Instagram Cloud IP 차단 문제

> 작성일: 2026-02-19
> 상태: **미해결**

## 현상

ZIP 파일을 업로드하면 일부 계정(`@littleghost_cafe` 등)이:

| 환경 | 결과 |
|------|------|
| 로컬 (자택 IP) | 활성 목록 + 프로필 사진 표시 |
| 운영 (unfollowlens.com) | 활성 목록 + 미확인 배지 (사진 없음) |

※ 운영 배포 전 구버전 캐시가 남아 있을 경우 "제외된 계정"으로 표시될 수 있음 → `_headers` 캐시 무효화로 해결됨

## 근본 원인

### Instagram의 클라우드 IP 감지

Instagram은 클라우드 서버 IP를 감지하여 프로필 페이지 대신 로그인 페이지를 반환한다.

```
클라우드 IP (Cloudflare / Google Cloud Run)
→ GET https://www.instagram.com/littleghost_cafe/
← HTTP 200, <title>Login • Instagram</title>  ← og 태그 없음

자택/레지덴셜 IP
→ GET https://www.instagram.com/littleghost_cafe/
← HTTP 200, <meta property="og:title" content="...">  ← 정상
```

`parseAccountFromHtml()`은 og 태그가 없으면 `deleted_or_restricted`를 반환하므로,
실제로 존재하는 계정이 확인 불가 상태로 처리된다.

## Fallback 체인 동작 분석

`check-account.js`의 fallback 체인은 아래와 같다:

```
1단계: Cloudflare IP 직접 요청
  ├─ 응답 200 + og 태그 있음 → active 반환 ✅
  ├─ 응답 200 + og 태그 없음 → deleted_or_restricted
  │     └─ Cloud Run fallback 시도 (아래 참조)
  ├─ 응답 404 → deleted 반환
  └─ 응답 429 → [429 fallback 체인] 진입
       ├─ Fallback 1: Cloud Run
       ├─ Fallback 2: ScraperAPI
       └─ Fallback 3: Dataimpulse (레지덴셜 프록시)
```

### Cloud Run fallback (200 + 로그인 월 케이스)

1단계에서 `deleted_or_restricted`가 나오면 Cloud Run으로 재시도한다:

```
Cloud Run (Google IP) → GET instagram.com/littleghost_cafe/
← HTTP 200, <title>Login • Instagram</title>  ← 동일하게 로그인 페이지
→ parseAccountFromHtml → deleted_or_restricted
→ retryResult.status !== 'deleted_or_restricted' 조건 실패
→ 개선 없이 deleted_or_restricted 반환
```

**결론: Cloud Run도 Google Cloud IP이므로 동일하게 차단됨.**

### Dataimpulse가 실행되지 않는 이유

Dataimpulse(레지덴셜 프록시)는 **429 전용 fallback 체인**에만 연결되어 있다.

```
현재 케이스: Instagram이 200을 반환 (로그인 페이지)
→ 429 fallback 체인 진입 조건 미충족
→ Dataimpulse 실행되지 않음
```

즉, 현재 아키텍처에서 Dataimpulse는 다음 조건이 **모두** 충족될 때만 실행된다:
1. Instagram이 HTTP **429**를 반환
2. Cloud Run 미설정 또는 Cloud Run도 429/에러
3. ScraperAPI 미설정 또는 ScraperAPI도 실패
4. `PROXY_HOST`, `PROXY_USER`, `PROXY_PASS` 환경변수 설정됨

현재는 Instagram이 200(로그인 페이지)을 반환하므로 Dataimpulse는 **절대 실행되지 않는다.**

## 현재 미해결 상태

### 문제 1: 200 로그인 월 케이스에서 레지덴셜 프록시 미사용

`deleted_or_restricted` 결과가 나왔을 때 Cloud Run 재시도 후에도 개선이 없으면,
Dataimpulse(레지덴셜 프록시)를 추가로 시도하는 로직이 없다.

**영향**: 실제 존재하는 계정이 `deleted_or_restricted` (미확인 배지)로 표시됨. 프로필 사진 없음.

**해결 방법**: Cloud Run fallback 후에도 `deleted_or_restricted`이면 Dataimpulse로 추가 시도

```
현재: Cloudflare → Cloud Run → (개선 없으면 포기)
개선: Cloudflare → Cloud Run → Dataimpulse → (최종 포기)
```

### 문제 2: Cloudflare Workers에서 Dataimpulse TCP 연결 신뢰성

`fetchViaProxy()` 구현은 `cloudflare:sockets`를 사용한 TCP 직접 연결이다.
Cloudflare Workers 프로덕션 환경에서 TLS 핸드셰이크 실패가 알려진 제한사항으로
보고되어 있어, 실제 작동 여부가 불확실하다.

참고: https://community.cloudflare.com/t/forward-proxy-via-cloudflare-sockets-and-starttls/862412

**영향**: Dataimpulse 연결이 프로덕션에서 실패할 가능성 있음.

**대안**: Dataimpulse HTTP API(표준 fetch)가 있다면 TCP 소켓 대신 사용

### 문제 3: Dataimpulse 환경변수 미설정 여부 불명확

`PROXY_HOST`, `PROXY_USER`, `PROXY_PASS`가 Cloudflare Pages 환경변수에
실제로 설정되어 있는지 확인이 필요하다. 설정되지 않은 경우 429 케이스에서도
Dataimpulse가 실행되지 않는다.

## 현재 사용자 경험 (배포 후 예상)

| 계정 유형 | API 응답 | UI 표시 |
|----------|---------|--------|
| 클라우드 IP에서 접근 가능한 계정 | `active` | 활성 목록 + 프로필 사진 |
| 클라우드 IP에서 로그인 월 (실제 존재) | `deleted_or_restricted` | 활성 목록 + 미확인 배지 |
| 실제 삭제/비활성 계정 | `deleted` | 제외된 계정 목록 |

## 해결 방안 후보

### 방안 A: 200 로그인 월 케이스에도 Dataimpulse 추가 (권장)

`check-account.js`에서 Cloud Run fallback 후에도 `deleted_or_restricted`이면
`fetchViaProxy()`를 추가로 시도한다.

우선 해결 과제:
1. Cloudflare Pages에 `PROXY_HOST`, `PROXY_USER`, `PROXY_PASS` 설정 확인
2. Dataimpulse TCP 연결이 실제로 동작하는지 확인 (429 케이스 발생 시 테스트)
3. 동작하면 200 케이스에도 Dataimpulse fallback 추가

### 방안 B: ScraperAPI를 200 로그인 월 케이스에도 추가

ScraperAPI는 `fetch()`로 동작하여 TCP 제한 없음. 현재는 429 케이스에만 연결됨.
`SCRAPER_API_KEY` 환경변수 설정 후 200+로그인 월 케이스에도 시도 가능.

비용: ScraperAPI 유료 플랜 필요.

### 방안 C: 현 상태 유지 (미확인 배지)

`deleted_or_restricted` 계정을 미확인 배지로 표시하고 사용자에게 판단 위임.
구현 비용 없음. 사용자 경험이 다소 불편하지만 허용 가능한 수준.
