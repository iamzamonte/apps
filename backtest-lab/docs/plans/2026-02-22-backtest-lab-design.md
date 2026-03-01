# BacktestLab - 한국/미국 주식 백테스트 앱 디자인

## 개요

한국(KRX)과 미국(NYSE/NASDAQ) 주식을 대상으로 자산 배분 전략을 백테스트할 수 있는 웹 애플리케이션.

## 핵심 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| 데이터 소스 | Yahoo Finance (yahoo-finance2) | 무료, 한국/미국 모두 지원, 안정적 |
| 전략 유형 | 자산 배분 (종목 비중 + 리밸런싱) | MVP에 적합, 대부분의 개인 투자자 사용 패턴 |
| 프론트엔드 | React + Vite + TypeScript | 차트 생태계 풍부, Cloudflare Pages 배포 간편 |
| 백엔드 | Cloudflare Workers | 서버리스, 무료 티어 10만 req/일, 관리 불필요 |
| 차트 | TradingView Lightweight Charts | 금융 특화, 60fps, ~40KB 번들 |
| 저장소 | LocalStorage | 인증 불필요, MVP에 적합 |
| 배포 | Cloudflare Pages + Workers | 통합 인프라 |

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                  사용자 브라우저                    │
│                                                   │
│  React + Vite (Cloudflare Pages)                  │
│  ┌───────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 전략 관리  │ │ 백테스트  │ │ TradingView      │ │
│  │ CRUD      │ │ 엔진     │ │ Lightweight Charts│ │
│  └─────┬─────┘ └────┬─────┘ └────────┬─────────┘ │
│        │            │                │            │
│        ▼            │                │            │
│  LocalStorage       │                │            │
│  (전략 저장)        │                │            │
└─────────────────────┼────────────────┼────────────┘
                      │                │
                      ▼                │
         ┌────────────────────┐        │
         │ Cloudflare Workers │        │
         │ /api/stocks        │        │
         └────────┬───────────┘        │
                  │
                  ▼
         ┌────────────────────┐
         │  Yahoo Finance API │
         └────────────────────┘
```

## 데이터 모델

### Portfolio (전략)

```typescript
interface Portfolio {
  id: string
  name: string
  description?: string
  assets: Asset[]
  rebalancing: RebalancingType
  backtestPeriod: BacktestPeriod
  createdAt: string
  updatedAt: string
}

interface Asset {
  symbol: string        // "AAPL", "005930.KS"
  name: string          // "Apple Inc.", "삼성전자"
  market: 'US' | 'KR'
  weight: number        // 0-100 (%), 합계 = 100
}

type RebalancingType =
  | 'monthly'
  | 'quarterly'
  | 'semi-annually'
  | 'annually'
  | 'none'

interface BacktestPeriod {
  startDate: string
  endDate: string
}
```

### BacktestResult (백테스트 결과)

```typescript
interface BacktestResult {
  portfolioId: string
  totalReturn: number
  annualizedReturn: number
  maxDrawdown: number
  sharpeRatio: number
  volatility: number
  timeline: TimelinePoint[]
}

interface TimelinePoint {
  date: string
  value: number
  drawdown: number
}
```

### 한국 주식 티커 규칙

- KOSPI: `005930.KS` (삼성전자)
- KOSDAQ: `035720.KQ` (카카오)
- 미국: `AAPL`, `SPY` (그대로)

## 페이지 구조

```
/                    → 대시보드 (전략 목록)
/portfolio/new       → 전략 생성
/portfolio/:id       → 전략 상세 + 백테스트 결과
/portfolio/:id/edit  → 전략 수정
```

### 1. 대시보드 (/)

- 전략 카드 그리드 (이름, 종목 요약, CAGR)
- 전략 없을 때 빈 상태 안내
- [+ 새 전략 만들기] 버튼

### 2. 전략 생성/수정

- 전략 이름, 설명 입력
- 종목 검색 + 추가 (심볼 입력 → 자동완성)
- 비중 입력 (합계 100% 검증)
- 리밸런싱 주기 선택 (라디오 버튼)
- 백테스트 기간 선택

### 3. 백테스트 결과

- 자산 배분 뱃지 (상단)
- 성과 요약 카드 (CAGR, 최대낙폭, 샤프비율, 변동성)
- 포트폴리오 가치 추이 차트 (Lightweight Charts)
- 드로다운 차트

## Workers API

```
GET /api/stocks?symbols=AAPL,005930.KS&startDate=2020-01-01&endDate=2025-12-31

Response: {
  "AAPL": [
    { "date": "2020-01-02", "close": 75.09 },
    ...
  ],
  "005930.KS": [
    { "date": "2020-01-02", "close": 55300 },
    ...
  ]
}
```
