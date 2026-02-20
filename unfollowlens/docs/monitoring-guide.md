# Unfollowlens 모니터링 가이드

> 최종 수정: 2026-02-20

## 1. 모니터링 대상 컴포넌트

```
사용자 브라우저
    │
    ▼
┌─────────────────────────────────────┐
│ Cloudflare Pages (unfollowlens.com) │
│  ├─ /api/check-account              │ ← 계정 상태 확인
│  └─ /api/proxy-image                │ ← 프로필 이미지 프록시
└──────────┬──────────────────────────┘
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
 Instagram  ScraperAPI  Cloud Run (us-east1)
                           │
                           ▼
                     Dataimpulse 프록시
                     (CONNECT + 이중 TLS)
                           │
                           ▼
                       Instagram
                    (레지덴셜 IP)
```

| 구간 | 서비스 | 장애 영향 |
|------|--------|----------|
| A | Cloudflare Pages | 전체 서비스 불가 |
| B | Cloud Run | fallback 실패 → 프로필 사진 누락, 잘못된 deleted 판정 |
| C | Dataimpulse 프록시 | Cloud Run 경유 요청 실패 |
| D | ScraperAPI | 429 fallback 실패 (Cloud Run으로 추가 fallback 존재) |
| E | Instagram | 업스트림 장애 — 대응 불가 |

## 2. Cloud Run 모니터링

### GCP 콘솔

**Cloud Run → unfollowlens-proxy → Metrics** 탭에서 확인:

- **Request count**: 요청 수 및 HTTP 상태 코드 분포
- **Request latency**: p50, p95, p99 응답 시간
- **Container instance count**: 활성 인스턴스 수
- **Billable container instance time**: 과금 시간

### gcloud CLI

```bash
# 서비스 상태 확인
gcloud run services describe unfollowlens-proxy \
  --region us-east1 \
  --format='yaml(status.conditions)'

# 최근 리비전 목록
gcloud run revisions list \
  --service unfollowlens-proxy \
  --region us-east1 \
  --limit 5

# 실시간 로그 스트리밍
gcloud run services logs tail unfollowlens-proxy \
  --region us-east1

# 최근 에러 로그만 필터링
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="unfollowlens-proxy"
   severity>=ERROR' \
  --limit 20 \
  --format='table(timestamp,textPayload)'
```

### /health 엔드포인트

```bash
curl -s -w '\nSTATUS:%{http_code} TIME:%{time_total}s' \
  https://unfollowlens-proxy-wsnnkkhd5q-ue.a.run.app/health
```

정상 응답: `{"status":"ok"}` (HTTP 200)

## 3. Cloudflare Pages 모니터링

### Cloudflare Dashboard

**Workers & Pages → unfollowlens → Analytics** 에서 확인:

- **Requests**: 총 요청 수, 성공/실패 비율
- **CPU Time**: Functions 실행 시간
- **Errors**: 에러 발생 빈도

### Functions 실시간 로그

**Workers & Pages → unfollowlens → Functions → Real-time Logs** 탭:
- 각 요청의 HTTP 상태, 실행 시간, 에러 메시지 확인 가능
- Production / Preview 환경 필터링

### wrangler CLI

```bash
# 실시간 로그 (로컬에서)
cd unfollowlens
npx wrangler pages deployment tail --project-name unfollowlens
```

## 4. 외부 서비스 상태 확인

### Instagram 직접 접근 테스트

```bash
# Cloudflare IP에서의 Instagram 응답 확인 (로그인 월/404/429 여부)
curl -s -o /dev/null -w '%{http_code}' \
  -H 'User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1)' \
  'https://www.instagram.com/instagram/'
```

### Dataimpulse 프록시 (Cloud Run 경유)

```bash
APIKEY=<CLOUD_RUN_API_KEY>
curl -s -w '\nSTATUS:%{http_code} TIME:%{time_total}s' \
  -H "x-api-key: ${APIKEY}" \
  'https://unfollowlens-proxy-wsnnkkhd5q-ue.a.run.app/check-account?username=instagram'
```

- 정상: HTTP 200 + Instagram HTML (og 태그 포함)
- 프록시 장애: HTTP 502 + `{"error":"Proxy environment variables not configured"}` 또는 TLS 에러
- 인증 실패: HTTP 401

### ScraperAPI 상태

```bash
# ScraperAPI 계정 잔여 크레딧 확인
curl -s "https://api.scraperapi.com/account?api_key=<SCRAPER_API_KEY>" | python3 -m json.tool
```

## 5. 수동 헬스 체크 커맨드

전체 파이프라인을 한 번에 점검하는 스크립트:

```bash
#!/bin/bash
APIKEY=<CLOUD_RUN_API_KEY>
CR_URL=https://unfollowlens-proxy-wsnnkkhd5q-ue.a.run.app
CF_URL=https://unfollowlens.com

echo "=== 1. Cloudflare Pages ==="
curl -s -o /dev/null -w 'STATUS:%{http_code} TIME:%{time_total}s' "$CF_URL/"
echo ""

echo "=== 2. check-account API (Cloudflare) ==="
curl -s "$CF_URL/api/check-account?username=instagram" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f\"status={d.get('status')} pic={'yes' if d.get('profile_pic_url') else 'no'}\")"

echo "=== 3. Cloud Run Health ==="
curl -s -w ' TIME:%{time_total}s' "$CR_URL/health"
echo ""

echo "=== 4. Cloud Run Proxy ==="
curl -s -w '\nSTATUS:%{http_code} TIME:%{time_total}s' \
  -H "x-api-key: ${APIKEY}" \
  "$CR_URL/check-account?username=instagram" | tail -1

echo "=== 5. proxy-image ==="
curl -s -o /dev/null -w 'STATUS:%{http_code} SIZE:%{size_download} TIME:%{time_total}s' \
  "$CF_URL/api/proxy-image?url=https%3A%2F%2Fscontent.cdninstagram.com%2Fv%2Ft51.2885-19%2F550891366_18667771684001321_1383210656577177067_n.jpg"
echo ""
```

### 기대 결과

| 단계 | 정상 | 이상 |
|------|------|------|
| 1. Cloudflare Pages | 200 | 5xx → Cloudflare 장애 |
| 2. check-account | `status=active`, `pic=yes` | `status=deleted` → fallback 미동작 |
| 3. Cloud Run Health | `{"status":"ok"}` | timeout → 인스턴스 미기동 |
| 4. Cloud Run Proxy | 200 + HTML | 502 → Dataimpulse 장애 / 환경변수 누락 |
| 5. proxy-image | 200 + SIZE > 0 | 400/502 → CDN URL 만료 또는 프록시 에러 |

## 6. Uptime 모니터링 설정

### Google Cloud Monitoring (Uptime Check)

```bash
# Cloud Run 헬스 체크 (5분 간격)
gcloud monitoring uptime create \
  --display-name="unfollowlens-proxy-health" \
  --resource-type=uptime-url \
  --hostname=unfollowlens-proxy-wsnnkkhd5q-ue.a.run.app \
  --path=/health \
  --port=443 \
  --protocol=https \
  --period=300 \
  --timeout=10
```

### UptimeRobot (무료 대안)

1. [uptimerobot.com](https://uptimerobot.com) 가입
2. Monitor 추가:

| Monitor | URL | Interval | Alert |
|---------|-----|----------|-------|
| Cloudflare Pages | `https://unfollowlens.com/` | 5분 | Email |
| Cloud Run Health | `https://unfollowlens-proxy-wsnnkkhd5q-ue.a.run.app/health` | 5분 | Email |
| API 기능 | `https://unfollowlens.com/api/check-account?username=instagram` | 15분 | Email |

**API Monitor 설정**: Response에 `"status":"active"` 포함 여부로 키워드 모니터링.

## 7. 장애 대응 체크리스트

### 증상: 프로필 사진이 표시되지 않음

```
1. check-account API 응답 확인
   └─ status=deleted → Cloud Run fallback 미동작
       ├─ CLOUD_RUN_URL 환경변수 확인 (Cloudflare Dashboard)
       ├─ CLOUD_RUN_API_KEY 환경변수 확인
       └─ Cloud Run 서비스 상태 확인
          └─ /health 200인데 /check-account 502
              ├─ PROXY_HOST/USER/PASS 환경변수 확인
              └─ Dataimpulse 계정 잔액/상태 확인

2. check-account API 응답 확인
   └─ status=active, profile_pic_url 있음 → proxy-image 문제
       ├─ /api/proxy-image?url=<pic_url> 직접 호출
       ├─ Instagram CDN URL 만료 여부 확인
       └─ 브라우저 콘솔에서 이미지 로드 에러 확인
```

### 증상: 모든 계정이 unknown으로 표시됨

```
1. Instagram 직접 접근 테스트
   └─ 429 → Rate limit 발생
       ├─ ScraperAPI 잔여 크레딧 확인
       ├─ Cloud Run 프록시 상태 확인
       └─ 요청 빈도 확인 (일시적 제한인지)
```

### 증상: Cloud Run 502 에러

```
1. /health 확인
   └─ 200 → 서비스 정상, 프록시 연결 문제
       ├─ PROXY_HOST/PORT/USER/PASS 확인
       ├─ Dataimpulse 서비스 상태 확인
       └─ 에러 로그 확인: gcloud run services logs tail unfollowlens-proxy --region us-east1
   └─ timeout → 인스턴스 미기동
       ├─ 리비전 상태 확인: gcloud run revisions list --service unfollowlens-proxy --region us-east1
       └─ 컨테이너 이미지 확인: gcloud run services describe unfollowlens-proxy --region us-east1
```

### 증상: Cloud Build 배포 실패

```
1. 빌드 로그 확인
   gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')

2. 단계별 확인
   ├─ Build 실패 → Dockerfile 또는 소스 코드 에러
   ├─ Push 실패 → GCR 권한 문제
   └─ Deploy 실패 → Cloud Run 서비스 설정 문제
```

## 8. 알림 설정 (Google Cloud Monitoring)

### Cloud Run 에러율 알림

```bash
gcloud alpha monitoring policies create \
  --display-name="unfollowlens-proxy-error-rate" \
  --condition-display-name="5xx error rate > 10%" \
  --condition-filter='
    resource.type="cloud_run_revision"
    AND resource.labels.service_name="unfollowlens-proxy"
    AND metric.type="run.googleapis.com/request_count"
    AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=10 \
  --condition-threshold-duration=300s \
  --notification-channels=<CHANNEL_ID>
```

### 알림 채널 생성 (이메일)

```bash
gcloud alpha monitoring channels create \
  --display-name="unfollowlens-alerts" \
  --type=email \
  --channel-labels=email_address=<YOUR_EMAIL>
```

### 권장 알림 정책

| 알림 | 조건 | 임계값 |
|------|------|--------|
| Cloud Run 에러율 | 5xx 비율 | > 10% (5분간) |
| Cloud Run 응답 지연 | p95 latency | > 15초 |
| Uptime 실패 | Health check 실패 | 2회 연속 |
| Cloud Build 실패 | 빌드 상태 | FAILURE |

### Cloud Build 실패 알림

GCP 콘솔 → **Cloud Build → Settings → Notifications**:
- Slack, Email, PubSub 등 연동 가능
- 빌드 실패 시 자동 알림

## 환경변수 체크리스트

장애 진단 시 가장 먼저 확인할 항목:

### Cloud Run

```bash
gcloud run services describe unfollowlens-proxy \
  --region us-east1 \
  --format='yaml(spec.template.spec.containers[0].env)'
```

| 변수 | 필수 | 확인 방법 |
|------|------|----------|
| `API_KEY` | 필수 | /health는 200이지만 /check-account가 401이면 누락 |
| `PROXY_HOST` | 필수 | 502 + "Proxy environment variables not configured" |
| `PROXY_PORT` | 선택 | 기본값 823 |
| `PROXY_USER` | 필수 | 502 + "Proxy environment variables not configured" |
| `PROXY_PASS` | 필수 | 502 + "Proxy environment variables not configured" |

### Cloudflare Pages

Cloudflare Dashboard → Pages → unfollowlens → Settings → Environment variables

| 변수 | 필수 | 확인 방법 |
|------|------|----------|
| `CLOUD_RUN_URL` | 필수 | check-account가 `deleted_or_restricted` 반환 시 누락 의심 |
| `CLOUD_RUN_API_KEY` | 필수 | Cloud Run 로그에 401 발생 |
| `SCRAPER_API_KEY` | 선택 | 429 시 ScraperAPI fallback 미동작 |
