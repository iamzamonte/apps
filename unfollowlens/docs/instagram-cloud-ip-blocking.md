# Instagram Cloud IP 차단 문제

> 작성일: 2026-02-19
> 상태: **로컬 검증 완료 — 배포 후 확인 필요**

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
  │     │   (CONNECT 터널 → inner TLS → HTTPS 요청)
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

## 진단 결과 (2026-02-20)

### 포트 823 = TLS (HTTPS 프록시)

로컬 테스트(`scripts/test-proxy.mjs`)로 확인한 결과, Dataimpulse 포트 823은 **평문 TCP가 아닌 TLS 소켓**이다.
따라서 기존 `secureTransport: 'off'` 방식으로 연결하면 즉시 끊긴다.

### CONNECT 터널링으로 전환한 이유

`GET https://www.instagram.com/...` 방식의 포워드 프록시 요청은 동작하지 않는다.
올바른 흐름:

```
1. TLS 소켓으로 프록시에 연결 (outer TLS)
2. CONNECT www.instagram.com:443 HTTP/1.1 전송
3. 프록시가 "200 Connection established" 반환
4. 동일 소켓 위에서 inner TLS 핸드셰이크 (이중 TLS)
5. HTTPS GET / 요청 전송
```

### 로컬 테스트 성공 결과

Node.js `tls.connect({ socket })` 이중 TLS로 `@littleghost_cafe` 검증:
- `status: active` 반환
- 프로필 사진 URL 포함
- `og:title`, `og:description` 태그 정상 파싱

### 프로덕션 구현 및 리스크

`check-account.js`는 CF Workers `outerSocket.startTls()` 이중 호출로 수정됨.
CF Workers의 `startTls()` 이중 호출이 공식 지원되지 않아 배포 환경에서 실패할 수 있다.

**실패 시 대안:** `node:tls` 기반 별도 프록시 워커 또는 외부 Node.js 서비스로 프록시 요청 위임.

## 현재 사용자 경험

| 계정 유형 | API 응답 | UI 표시 |
|----------|---------|--------|
| 정상 접근 가능한 계정 | `active` | 활성 목록 + 프로필 사진 |
| Dataimpulse로 접근 성공한 계정 | `active` | 활성 목록 + 프로필 사진 |
| Dataimpulse도 로그인 월 반환 | `deleted_or_restricted` | 활성 목록 + 확인불가 배지 |
| 실제 삭제/비활성 계정 | `deleted` | 제외된 계정 목록 |
