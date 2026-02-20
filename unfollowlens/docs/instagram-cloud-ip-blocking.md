# Instagram Cloud IP 차단 문제

> 작성일: 2026-02-19
> 최종 수정: 2026-02-20
> 상태: **해결됨**

## 현상

ZIP 파일을 업로드하면 일부 계정(`@littleghost_cafe` 등)이:

| 환경 | 결과 |
|------|------|
| 로컬 (자택 IP) | 활성 목록 + 프로필 사진 표시 |
| 운영 (unfollowlens.com) | "삭제됨"으로 잘못 분류 (사진 없음) |

## 근본 원인

### Instagram의 클라우드 IP 감지

Instagram은 클라우드 서버 IP를 감지하여 프로필 페이지 대신 **로그인 페이지** 또는 **404**를 반환한다.

```
클라우드 IP (Cloudflare / Google Cloud Run)
→ GET https://www.instagram.com/littleghost_cafe/
← HTTP 200, <title>Login • Instagram</title>  ← og 태그 없음
← 또는 HTTP 404                                ← 유효 계정도 404 반환

자택/레지덴셜 IP
→ GET https://www.instagram.com/littleghost_cafe/
← HTTP 200, <meta property="og:title" content="...">  ← 정상
```

`parseAccountFromHtml()`은 og 태그가 없으면 `deleted_or_restricted`를 반환하므로,
실제로 존재하는 계정이 확인 불가 또는 삭제 상태로 처리된다.

## 해결 과정

### Issue 1: Cloudflare Workers `startTls()` 이중 TLS 미지원

**문제**: Dataimpulse 레지덴셜 프록시는 CONNECT 터널 + 이중 TLS가 필요.
Cloudflare Workers의 `startTls()`는 이중 호출을 공식 지원하지 않아 프로덕션에서 실패.

**시도한 방법**:
1. `cloudflare:sockets` API의 `startTls()` 이중 호출 → 프로덕션에서 불안정
2. `node:tls` (`nodejs_compat` 플래그) → Cloudflare Workers에서 완전한 `tls.connect({ socket })` 미지원

**해결**: 이중 TLS 로직을 **Google Cloud Run**으로 이전.
Cloud Run은 Node.js 22를 완전하게 지원하므로 `node:tls`의 `tls.connect({ socket })` 이중 TLS가 정상 동작.

```
[변경 전] Cloudflare Worker → Dataimpulse (이중 TLS 직접 처리) → Instagram
[변경 후] Cloudflare Worker → Cloud Run → Dataimpulse (이중 TLS) → Instagram
```

**관련 커밋**: `e5c5f84` — refactor: 이중 TLS 프록시 로직을 Cloudflare Worker에서 Cloud Run으로 이전

### Issue 2: Cloud Build Docker 빌드 에러

**문제**: `cloudbuild.yaml`에서 Docker 빌드 시 에러 발생.

```
Error response from daemon: unexpected error reading Dockerfile:
read /var/lib/docker/tmp/.../cloud-run: is a directory
```

Docker가 build context(`unfollowlens/cloud-run`)를 Dockerfile로 읽으려 시도.

**시도한 방법**:
1. `-f unfollowlens/cloud-run/Dockerfile` 플래그 추가 → 동일 에러 (build context 경로 해석 문제)

**해결**: `dir` 필드로 작업 디렉토리를 명시적으로 설정하고 `.`으로 build context 지정.

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    dir: unfollowlens/cloud-run    # 작업 디렉토리 명시
    args:
      - build
      - -t
      - gcr.io/$PROJECT_ID/unfollowlens-proxy:$COMMIT_SHA
      - .                          # 현재 디렉토리 = build context
```

추가로 push + deploy 단계를 파이프라인에 통합하여 빌드-푸시-배포 자동화 완료.

**관련 커밋**: `b07709e`, `37ce275`

### Issue 3: Instagram 404 응답에 Cloud Run fallback 누락

**문제**: Instagram이 클라우드 IP에 대해 유효한 계정도 **404**를 반환하는 경우가 있음.
기존 코드는 404를 받으면 Cloud Run fallback 없이 즉시 `"deleted"`로 반환.

```
429 → Cloud Run fallback 있음 ✅
200 + 로그인 월 → Cloud Run fallback 있음 ✅
404 → Cloud Run fallback 없음 ❌  ← 버그
```

**증거**:
- Cloudflare API 응답: `{"status":"deleted","accessible":false}` (profile_pic_url 없음)
- Cloud Run 직접 호출: HTTP 200, og:image 정상 반환 (427 Followers, 프로필 사진 포함)

**해결**: 404 핸들러에 Cloud Run fallback 추가.
Cloud Run이 200을 반환하면 실제 상태를 판단하고, Cloud Run도 404이면 진짜 삭제된 계정으로 처리.

```javascript
if (response.status === 404) {
  if (hasCloudRunConfig(env)) {
    try {
      const proxyResult = await fetchViaCloudRun(profileUrl, env);
      if (proxyResult.status === 200) {
        const result = parseAccountFromHtml(proxyResult.body, sanitizedUsername);
        return jsonResponse(result);
      }
    } catch {
      // Cloud Run 실패 → 원래 404 결과 반환
    }
  }
  return jsonResponse({ username, status: 'deleted', accessible: false });
}
```

## 현재 아키텍처

```
사용자 → unfollowlens.com (Cloudflare Pages)
             │
             ▼
      check-account.js (Cloudflare Pages Function)
             │
             ├─ 1단계: Cloudflare IP로 Instagram 직접 요청
             │
             ├─ 200 + og 태그 → active ✅
             │
             ├─ 200 + 로그인 월 (og 태그 없음) ─┐
             ├─ 404 ─────────────────────────────┤
             │                                    ▼
             │                       Cloud Run (us-east1)
             │                           │
             │                           ▼
             │                    Dataimpulse 레지덴셜 프록시
             │                    (CONNECT 터널 + 이중 TLS)
             │                           │
             │                           ▼
             │                       Instagram
             │                           │
             │                    ┌──────┴──────┐
             │                    ▼              ▼
             │               200 + og        404/실패
             │               → active ✅     → deleted
             │
             └─ 429 → ScraperAPI → Cloud Run → unknown
```

## Fallback 체인

```
1단계: Cloudflare IP 직접 요청
  ├─ 200 + og 태그 있음 → active ✅
  ├─ 200 + og 태그 없음 (로그인 월) → Cloud Run으로 재시도
  │     ├─ Cloud Run 200 + og 태그 있음 → active ✅
  │     ├─ Cloud Run 200 + og 태그 없음 → deleted_or_restricted
  │     ├─ Cloud Run 404 → deleted
  │     └─ Cloud Run 실패/미설정 → deleted_or_restricted
  ├─ 404 → Cloud Run으로 재시도
  │     ├─ Cloud Run 200 + og 태그 있음 → active ✅
  │     └─ Cloud Run 404/실패/미설정 → deleted
  └─ 429 → [429 fallback 체인]
       ├─ Fallback 1: ScraperAPI
       ├─ Fallback 2: Cloud Run
       └─ Fallback 없음 → unknown
```

## 환경변수

### Cloud Run (`unfollowlens-proxy`)

| 변수 | 설명 |
|------|------|
| `API_KEY` | Cloudflare와 공유하는 인증 키 |
| `PROXY_HOST` | Dataimpulse 프록시 호스트 (예: `gw.dataimpulse.com`) |
| `PROXY_PORT` | Dataimpulse 프록시 포트 (기본값: `823`) |
| `PROXY_USER` | Dataimpulse 로그인 |
| `PROXY_PASS` | Dataimpulse 비밀번호 |

### Cloudflare Pages (`unfollowlens`)

| 변수 | 설명 |
|------|------|
| `CLOUD_RUN_URL` | Cloud Run 서비스 URL |
| `CLOUD_RUN_API_KEY` | Cloud Run 인증 키 |
| `SCRAPER_API_KEY` | ScraperAPI 키 (429 fallback용) |

## 이중 TLS 흐름 (Cloud Run 내부)

```
1. tls.connect(proxy:823)          [outer TLS — 프록시 인증]
2. CONNECT instagram.com:443 → 200 OK
3. tls.connect({ socket })         [inner TLS — instagram.com]
4. GET /username/ HTTP/1.0         → HTML 반환
```

Cloudflare Workers는 이중 TLS를 지원하지 않으므로,
`node:tls`가 완전히 동작하는 Cloud Run에서 프록시 연결을 처리한다.

## 현재 사용자 경험

| 계정 유형 | API 응답 | UI 표시 |
|----------|---------|--------|
| 정상 접근 가능한 계정 | `active` | 활성 목록 + 프로필 사진 |
| Cloud Run으로 접근 성공한 계정 | `active` | 활성 목록 + 프로필 사진 |
| Cloud Run도 로그인 월 반환 | `deleted_or_restricted` | 활성 목록 + 확인불가 배지 |
| Cloud Run도 404 반환 (진짜 삭제) | `deleted` | 제외된 계정 목록 |
