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

## 현재 Fallback 체인 (Cloud Run 제거 후)

`check-account.js`의 fallback 체인:

```
1단계: Cloudflare IP 직접 요청
  ├─ 200 + og 태그 있음 → active ✅
  ├─ 200 + og 태그 없음 (로그인 월) → Dataimpulse로 재시도
  │     ├─ Dataimpulse 200 + og 태그 있음 → active ✅
  │     ├─ Dataimpulse 200 + og 태그 없음 → deleted_or_restricted
  │     ├─ Dataimpulse 404 → deleted
  │     └─ Dataimpulse 실패/미설정 → deleted_or_restricted
  ├─ 404 → deleted
  └─ 429 → [429 fallback 체인]
       ├─ Fallback 1: ScraperAPI
       ├─ Fallback 2: Dataimpulse
       └─ Fallback 없음 → unknown
```

## 미해결 상태

### 문제: Cloudflare Workers에서 Dataimpulse TCP 연결 신뢰성

`fetchViaProxy()` 구현은 `cloudflare:sockets`를 사용한 TCP 직접 연결이다.
Cloudflare Workers 프로덕션 환경에서 TLS 핸드셰이크 실패가 알려진 제한사항으로
보고되어 있어, 실제 작동 여부가 불확실하다.

참고: https://community.cloudflare.com/t/forward-proxy-via-cloudflare-sockets-and-starttls/862412

**영향**: Dataimpulse 연결이 프로덕션에서 실패할 가능성 있음. 이 경우 `deleted_or_restricted` (확인불가 배지)로 표시됨.

**대안**: Dataimpulse HTTP API(표준 fetch)가 있다면 TCP 소켓 대신 사용

## 현재 사용자 경험

| 계정 유형 | API 응답 | UI 표시 |
|----------|---------|--------|
| 정상 접근 가능한 계정 | `active` | 활성 목록 + 프로필 사진 |
| Dataimpulse로 접근 성공한 계정 | `active` | 활성 목록 + 프로필 사진 |
| Dataimpulse도 로그인 월 반환 | `deleted_or_restricted` | 활성 목록 + 확인불가 배지 |
| 실제 삭제/비활성 계정 | `deleted` | 제외된 계정 목록 |
