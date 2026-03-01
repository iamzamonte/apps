# BacktestLab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 한국/미국 주식 자산 배분 전략을 백테스트하고 시각화하는 웹 애플리케이션 구현

**Architecture:** React + Vite SPA를 Cloudflare Pages에 배포하고, Cloudflare Pages Functions로 Yahoo Finance API를 프록시한다. 백테스트 계산은 클라이언트 사이드에서 순수 함수로 처리하며, 전략 데이터는 LocalStorage에 저장한다.

**Tech Stack:** React 19, Vite, TypeScript, TradingView Lightweight Charts, React Router, Vitest, Cloudflare Pages + Functions, yahoo-finance2

---

## Task 1: Project Scaffolding

**Files:**
- Create: `package.json`
- Create: `vite.config.ts`
- Create: `tsconfig.json`
- Create: `tsconfig.node.json`
- Create: `wrangler.jsonc`
- Create: `index.html`
- Create: `src/main.tsx`
- Create: `src/App.tsx`
- Create: `src/vite-env.d.ts`
- Create: `vitest.config.ts`
- Create: `eslint.config.js`
- Create: `.prettierrc`

**Step 1: Initialize project with Vite**

```bash
cd /Users/montecarlo/Downloads/2_AREA/apps/backtest-lab
npm create vite@latest . -- --template react-ts
```

Select: React, TypeScript

**Step 2: Install core dependencies**

```bash
npm install react-router-dom lightweight-charts
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @testing-library/user-event
npm install -D wrangler @cloudflare/workers-types
npm install -D eslint prettier eslint-config-prettier
npm install -D @types/react @types/react-dom
```

**Step 3: Configure wrangler.jsonc**

Create `wrangler.jsonc`:
```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "backtest-lab",
  "pages_build_output_dir": "./dist",
  "compatibility_date": "2025-04-01",
  "compatibility_flags": ["nodejs_compat"]
}
```

**Step 4: Configure vitest**

Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
    coverage: {
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/main.tsx', 'src/vite-env.d.ts'],
    },
  },
})
```

Create `tests/setup.ts`:
```typescript
import '@testing-library/jest-dom/vitest'
```

**Step 5: Create minimal App shell with React Router**

Create `src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<div>Dashboard</div>} />
        <Route path="/portfolio/new" element={<div>New</div>} />
        <Route path="/portfolio/:id" element={<div>Detail</div>} />
        <Route path="/portfolio/:id/edit" element={<div>Edit</div>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

**Step 6: Verify dev server starts**

```bash
npm run dev
```

Expected: Vite dev server starts on localhost:5173

**Step 7: Verify tests run**

```bash
npx vitest run
```

Expected: No test suites found (or 0 passed)

**Step 8: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold backtest-lab with Vite + React + TypeScript + Cloudflare"
```

---

## Task 2: Types & LocalStorage CRUD

**Files:**
- Create: `src/types.ts`
- Create: `src/lib/storage.ts`
- Create: `tests/lib/storage.test.ts`

**Step 1: Write types**

Create `src/types.ts`:
```typescript
export interface Portfolio {
  id: string
  name: string
  description: string
  assets: Asset[]
  rebalancing: RebalancingType
  backtestPeriod: BacktestPeriod
  createdAt: string
  updatedAt: string
}

export interface Asset {
  symbol: string
  name: string
  market: 'US' | 'KR'
  weight: number
}

export type RebalancingType =
  | 'monthly'
  | 'quarterly'
  | 'semi-annually'
  | 'annually'
  | 'none'

export interface BacktestPeriod {
  startDate: string
  endDate: string
}

export interface BacktestResult {
  portfolioId: string
  totalReturn: number
  annualizedReturn: number
  maxDrawdown: number
  sharpeRatio: number
  volatility: number
  timeline: TimelinePoint[]
}

export interface TimelinePoint {
  date: string
  value: number
  drawdown: number
}

export interface StockData {
  [symbol: string]: StockPrice[]
}

export interface StockPrice {
  date: string
  close: number
}
```

**Step 2: Write failing tests for storage**

Create `tests/lib/storage.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import {
  getPortfolios,
  getPortfolio,
  createPortfolio,
  updatePortfolio,
  deletePortfolio,
} from '../../src/lib/storage'
import type { Portfolio } from '../../src/types'

const mockPortfolio: Omit<Portfolio, 'id' | 'createdAt' | 'updatedAt'> = {
  name: 'Test Strategy',
  description: 'A test portfolio',
  assets: [
    { symbol: 'AAPL', name: 'Apple Inc.', market: 'US', weight: 60 },
    { symbol: '005930.KS', name: '삼성전자', market: 'KR', weight: 40 },
  ],
  rebalancing: 'quarterly',
  backtestPeriod: { startDate: '2020-01-01', endDate: '2025-12-31' },
}

beforeEach(() => {
  localStorage.clear()
})

describe('getPortfolios', () => {
  it('returns empty array when no portfolios exist', () => {
    expect(getPortfolios()).toEqual([])
  })

  it('returns all saved portfolios', () => {
    createPortfolio(mockPortfolio)
    createPortfolio({ ...mockPortfolio, name: 'Second Strategy' })
    expect(getPortfolios()).toHaveLength(2)
  })
})

describe('createPortfolio', () => {
  it('creates a portfolio with generated id and timestamps', () => {
    const result = createPortfolio(mockPortfolio)
    expect(result.id).toBeDefined()
    expect(result.name).toBe('Test Strategy')
    expect(result.createdAt).toBeDefined()
    expect(result.updatedAt).toBeDefined()
  })

  it('persists to localStorage', () => {
    createPortfolio(mockPortfolio)
    const stored = getPortfolios()
    expect(stored).toHaveLength(1)
    expect(stored[0].name).toBe('Test Strategy')
  })
})

describe('getPortfolio', () => {
  it('returns portfolio by id', () => {
    const created = createPortfolio(mockPortfolio)
    const found = getPortfolio(created.id)
    expect(found).toEqual(created)
  })

  it('returns undefined for non-existent id', () => {
    expect(getPortfolio('non-existent')).toBeUndefined()
  })
})

describe('updatePortfolio', () => {
  it('updates portfolio fields immutably', () => {
    const created = createPortfolio(mockPortfolio)
    const updated = updatePortfolio(created.id, { name: 'Updated Name' })
    expect(updated.name).toBe('Updated Name')
    expect(updated.id).toBe(created.id)
    expect(updated.createdAt).toBe(created.createdAt)
    expect(updated.updatedAt).not.toBe(created.updatedAt)
  })

  it('throws for non-existent id', () => {
    expect(() => updatePortfolio('bad-id', { name: 'x' })).toThrow()
  })
})

describe('deletePortfolio', () => {
  it('removes portfolio from storage', () => {
    const created = createPortfolio(mockPortfolio)
    deletePortfolio(created.id)
    expect(getPortfolios()).toHaveLength(0)
  })

  it('throws for non-existent id', () => {
    expect(() => deletePortfolio('bad-id')).toThrow()
  })
})
```

**Step 3: Run tests to verify they fail**

```bash
npx vitest run tests/lib/storage.test.ts
```

Expected: FAIL — module `../../src/lib/storage` not found

**Step 4: Implement storage module**

Create `src/lib/storage.ts`:
```typescript
import type { Portfolio } from '../types'

const STORAGE_KEY = 'backtest-lab-portfolios'

function readAll(): Portfolio[] {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    return JSON.parse(raw) as Portfolio[]
  } catch {
    console.error('Failed to parse portfolios from localStorage')
    return []
  }
}

function writeAll(portfolios: Portfolio[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(portfolios))
}

export function getPortfolios(): Portfolio[] {
  return readAll()
}

export function getPortfolio(id: string): Portfolio | undefined {
  return readAll().find((p) => p.id === id)
}

export function createPortfolio(
  data: Omit<Portfolio, 'id' | 'createdAt' | 'updatedAt'>
): Portfolio {
  const now = new Date().toISOString()
  const portfolio: Portfolio = {
    ...data,
    id: crypto.randomUUID(),
    createdAt: now,
    updatedAt: now,
  }
  writeAll([...readAll(), portfolio])
  return portfolio
}

export function updatePortfolio(
  id: string,
  data: Partial<Omit<Portfolio, 'id' | 'createdAt' | 'updatedAt'>>
): Portfolio {
  const portfolios = readAll()
  const index = portfolios.findIndex((p) => p.id === id)
  if (index === -1) throw new Error(`Portfolio not found: ${id}`)
  const updated: Portfolio = {
    ...portfolios[index],
    ...data,
    updatedAt: new Date().toISOString(),
  }
  writeAll([...portfolios.slice(0, index), updated, ...portfolios.slice(index + 1)])
  return updated
}

export function deletePortfolio(id: string): void {
  const portfolios = readAll()
  const index = portfolios.findIndex((p) => p.id === id)
  if (index === -1) throw new Error(`Portfolio not found: ${id}`)
  writeAll(portfolios.filter((p) => p.id !== id))
}
```

**Step 5: Run tests to verify they pass**

```bash
npx vitest run tests/lib/storage.test.ts
```

Expected: All 8 tests PASS

**Step 6: Commit**

```bash
git add src/types.ts src/lib/storage.ts tests/lib/storage.test.ts tests/setup.ts
git commit -m "feat: add portfolio types and LocalStorage CRUD with tests"
```

---

## Task 3: Backtest Engine (Core Logic)

**Files:**
- Create: `src/lib/backtest-engine.ts`
- Create: `tests/lib/backtest-engine.test.ts`

**Step 1: Write failing tests for backtest engine**

Create `tests/lib/backtest-engine.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { runBacktest } from '../../src/lib/backtest-engine'
import type { Portfolio, StockData } from '../../src/types'

const mockPortfolio: Portfolio = {
  id: '1',
  name: 'Test',
  description: '',
  assets: [
    { symbol: 'A', name: 'Stock A', market: 'US', weight: 50 },
    { symbol: 'B', name: 'Stock B', market: 'US', weight: 50 },
  ],
  rebalancing: 'none',
  backtestPeriod: { startDate: '2024-01-01', endDate: '2024-01-05' },
  createdAt: '',
  updatedAt: '',
}

// Stock A: 100 → 110 (+10%)
// Stock B: 200 → 220 (+10%)
// Portfolio: +10% (both equal weight, both +10%)
const mockStockData: StockData = {
  A: [
    { date: '2024-01-01', close: 100 },
    { date: '2024-01-02', close: 102 },
    { date: '2024-01-03', close: 98 },
    { date: '2024-01-04', close: 105 },
    { date: '2024-01-05', close: 110 },
  ],
  B: [
    { date: '2024-01-01', close: 200 },
    { date: '2024-01-02', close: 198 },
    { date: '2024-01-03', close: 210 },
    { date: '2024-01-04', close: 205 },
    { date: '2024-01-05', close: 220 },
  ],
}

describe('runBacktest', () => {
  it('returns correct total return', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.totalReturn).toBeCloseTo(10, 0)
  })

  it('returns timeline with correct length', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.timeline).toHaveLength(5)
  })

  it('starts timeline at initial value of 10000', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.timeline[0].value).toBe(10000)
  })

  it('ends timeline at correct final value', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.timeline[4].value).toBeCloseTo(11000, 0)
  })

  it('calculates max drawdown as negative percentage', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.maxDrawdown).toBeLessThanOrEqual(0)
  })

  it('calculates annualized return (CAGR)', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.annualizedReturn).toBeDefined()
    expect(typeof result.annualizedReturn).toBe('number')
  })

  it('calculates sharpe ratio', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.sharpeRatio).toBeDefined()
    expect(typeof result.sharpeRatio).toBe('number')
  })

  it('calculates volatility', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.volatility).toBeDefined()
    expect(result.volatility).toBeGreaterThanOrEqual(0)
  })

  it('sets portfolioId correctly', () => {
    const result = runBacktest(mockPortfolio, mockStockData)
    expect(result.portfolioId).toBe('1')
  })
})

describe('runBacktest with rebalancing', () => {
  const monthlyPortfolio: Portfolio = {
    ...mockPortfolio,
    rebalancing: 'monthly',
    backtestPeriod: { startDate: '2024-01-01', endDate: '2024-03-01' },
  }

  const longStockData: StockData = {
    A: Array.from({ length: 61 }, (_, i) => ({
      date: new Date(2024, 0, 1 + i).toISOString().split('T')[0],
      close: 100 + i * 0.5,
    })),
    B: Array.from({ length: 61 }, (_, i) => ({
      date: new Date(2024, 0, 1 + i).toISOString().split('T')[0],
      close: 200 - i * 0.3,
    })),
  }

  it('produces valid result with monthly rebalancing', () => {
    const result = runBacktest(monthlyPortfolio, longStockData)
    expect(result.timeline.length).toBeGreaterThan(0)
    expect(result.totalReturn).toBeDefined()
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/lib/backtest-engine.test.ts
```

Expected: FAIL — module not found

**Step 3: Implement backtest engine**

Create `src/lib/backtest-engine.ts`:
```typescript
import type { Portfolio, StockData, BacktestResult, TimelinePoint } from '../types'

const INITIAL_VALUE = 10000
const RISK_FREE_RATE = 0.04 // 4% annual
const TRADING_DAYS_PER_YEAR = 252

function getRebalanceDates(
  dates: string[],
  rebalancing: Portfolio['rebalancing']
): Set<string> {
  if (rebalancing === 'none') return new Set()

  const intervals: Record<string, number> = {
    monthly: 1,
    quarterly: 3,
    'semi-annually': 6,
    annually: 12,
  }

  const monthInterval = intervals[rebalancing]
  const rebalanceDates = new Set<string>()
  let lastRebalanceMonth = -1

  for (const date of dates) {
    const month = new Date(date).getMonth()
    if (lastRebalanceMonth === -1) {
      lastRebalanceMonth = month
      continue
    }
    const diff = (month - lastRebalanceMonth + 12) % 12
    if (diff >= monthInterval) {
      rebalanceDates.add(date)
      lastRebalanceMonth = month
    }
  }

  return rebalanceDates
}

export function runBacktest(
  portfolio: Portfolio,
  stockData: StockData
): BacktestResult {
  const symbols = portfolio.assets.map((a) => a.symbol)
  const weights = portfolio.assets.map((a) => a.weight / 100)

  // Get common dates across all symbols
  const dateSets = symbols.map(
    (s) => new Set(stockData[s]?.map((d) => d.date) ?? [])
  )
  const allDates = stockData[symbols[0]]
    ?.map((d) => d.date)
    .filter((date) => dateSets.every((ds) => ds.has(date)))
    .sort() ?? []

  if (allDates.length < 2) {
    return {
      portfolioId: portfolio.id,
      totalReturn: 0,
      annualizedReturn: 0,
      maxDrawdown: 0,
      sharpeRatio: 0,
      volatility: 0,
      timeline: [],
    }
  }

  // Build price lookup
  const priceLookup: Record<string, Record<string, number>> = {}
  for (const symbol of symbols) {
    priceLookup[symbol] = {}
    for (const point of stockData[symbol] ?? []) {
      priceLookup[symbol][point.date] = point.close
    }
  }

  const rebalanceDates = getRebalanceDates(allDates, portfolio.rebalancing)

  // Initialize shares based on weights
  let currentWeights = [...weights]
  let portfolioValue = INITIAL_VALUE
  let shares = symbols.map((symbol, i) => {
    const price = priceLookup[symbol][allDates[0]]
    return (portfolioValue * currentWeights[i]) / price
  })

  const timeline: TimelinePoint[] = []
  let peak = INITIAL_VALUE
  let maxDrawdown = 0
  const dailyReturns: number[] = []
  let prevValue = INITIAL_VALUE

  for (const date of allDates) {
    // Calculate current portfolio value
    portfolioValue = symbols.reduce((sum, symbol, i) => {
      return sum + shares[i] * priceLookup[symbol][date]
    }, 0)

    // Track daily returns (skip first day)
    if (date !== allDates[0]) {
      dailyReturns.push((portfolioValue - prevValue) / prevValue)
    }
    prevValue = portfolioValue

    // Track drawdown
    if (portfolioValue > peak) peak = portfolioValue
    const drawdown = ((portfolioValue - peak) / peak) * 100
    if (drawdown < maxDrawdown) maxDrawdown = drawdown

    timeline.push({
      date,
      value: Math.round(portfolioValue * 100) / 100,
      drawdown: Math.round(drawdown * 100) / 100,
    })

    // Rebalance if needed
    if (rebalanceDates.has(date)) {
      shares = symbols.map((symbol, i) => {
        const price = priceLookup[symbol][date]
        return (portfolioValue * weights[i]) / price
      })
    }
  }

  const finalValue = timeline[timeline.length - 1].value
  const totalReturn = ((finalValue - INITIAL_VALUE) / INITIAL_VALUE) * 100

  // Annualized return (CAGR)
  const years = allDates.length / TRADING_DAYS_PER_YEAR
  const annualizedReturn =
    years > 0
      ? (Math.pow(finalValue / INITIAL_VALUE, 1 / years) - 1) * 100
      : 0

  // Volatility (annualized standard deviation)
  const meanReturn =
    dailyReturns.reduce((sum, r) => sum + r, 0) / dailyReturns.length
  const variance =
    dailyReturns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) /
    (dailyReturns.length - 1 || 1)
  const dailyVolatility = Math.sqrt(variance)
  const volatility = dailyVolatility * Math.sqrt(TRADING_DAYS_PER_YEAR) * 100

  // Sharpe Ratio
  const sharpeRatio =
    volatility > 0
      ? (annualizedReturn - RISK_FREE_RATE * 100) / volatility
      : 0

  return {
    portfolioId: portfolio.id,
    totalReturn: Math.round(totalReturn * 100) / 100,
    annualizedReturn: Math.round(annualizedReturn * 100) / 100,
    maxDrawdown: Math.round(maxDrawdown * 100) / 100,
    sharpeRatio: Math.round(sharpeRatio * 100) / 100,
    volatility: Math.round(volatility * 100) / 100,
    timeline,
  }
}
```

**Step 4: Run tests to verify they pass**

```bash
npx vitest run tests/lib/backtest-engine.test.ts
```

Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add src/lib/backtest-engine.ts tests/lib/backtest-engine.test.ts
git commit -m "feat: implement backtest engine with CAGR, drawdown, sharpe, volatility"
```

---

## Task 4: Cloudflare Workers API (Yahoo Finance Proxy)

**Files:**
- Create: `functions/api/stocks.ts`
- Create: `tests/api/stocks.test.ts`

**Step 1: Install yahoo-finance2**

```bash
npm install yahoo-finance2
```

**Step 2: Write the Workers function**

Create `functions/api/stocks.ts`:
```typescript
import yahooFinance from 'yahoo-finance2'

interface Env {}

interface StockPrice {
  date: string
  close: number
}

function errorResponse(message: string, status = 400): Response {
  return Response.json({ error: message }, { status })
}

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const url = new URL(context.request.url)
  const symbolsParam = url.searchParams.get('symbols')
  const startDate = url.searchParams.get('startDate')
  const endDate = url.searchParams.get('endDate')

  if (!symbolsParam || !startDate || !endDate) {
    return errorResponse('Missing required parameters: symbols, startDate, endDate')
  }

  const symbols = symbolsParam.split(',').map((s) => s.trim()).filter(Boolean)

  if (symbols.length === 0) {
    return errorResponse('No valid symbols provided')
  }

  if (symbols.length > 10) {
    return errorResponse('Maximum 10 symbols allowed')
  }

  try {
    const results: Record<string, StockPrice[]> = {}

    await Promise.all(
      symbols.map(async (symbol) => {
        const data = await yahooFinance.chart(symbol, {
          period1: startDate,
          period2: endDate,
          interval: '1d',
        })

        results[symbol] = (data.quotes ?? [])
          .filter((q) => q.close !== null && q.close !== undefined)
          .map((q) => ({
            date: new Date(q.date).toISOString().split('T')[0],
            close: q.close as number,
          }))
      })
    )

    return Response.json(results, {
      headers: {
        'Cache-Control': 'public, max-age=3600, s-maxage=86400',
        'Access-Control-Allow-Origin': '*',
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch stock data'
    console.error('Yahoo Finance API error:', message)
    return errorResponse(message, 502)
  }
}
```

**Step 3: Write API client for frontend**

Create `src/lib/api.ts`:
```typescript
import type { StockData } from '../types'

const API_BASE = '/api'

export async function fetchStockData(
  symbols: string[],
  startDate: string,
  endDate: string
): Promise<StockData> {
  const params = new URLSearchParams({
    symbols: symbols.join(','),
    startDate,
    endDate,
  })

  const response = await fetch(`${API_BASE}/stocks?${params}`)

  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(body.error || `HTTP ${response.status}`)
  }

  return response.json()
}
```

**Step 4: Write tests for API client**

Create `tests/lib/api.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchStockData } from '../../src/lib/api'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
})

describe('fetchStockData', () => {
  it('calls correct URL with params', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ AAPL: [] }),
    })

    await fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/stocks?symbols=AAPL&startDate=2024-01-01&endDate=2024-12-31'
    )
  })

  it('returns parsed stock data', async () => {
    const mockData = {
      AAPL: [{ date: '2024-01-02', close: 185.5 }],
    }
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const result = await fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')
    expect(result).toEqual(mockData)
  })

  it('throws on error response', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 502,
      json: () => Promise.resolve({ error: 'Failed to fetch' }),
    })

    await expect(
      fetchStockData(['AAPL'], '2024-01-01', '2024-12-31')
    ).rejects.toThrow('Failed to fetch')
  })

  it('joins multiple symbols with comma', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })

    await fetchStockData(['AAPL', '005930.KS'], '2024-01-01', '2024-12-31')

    const calledUrl = mockFetch.mock.calls[0][0] as string
    expect(calledUrl).toContain('symbols=AAPL%2C005930.KS')
  })
})
```

**Step 5: Run tests to verify they pass**

```bash
npx vitest run tests/lib/api.test.ts
```

Expected: All 4 tests PASS

**Step 6: Commit**

```bash
git add functions/api/stocks.ts src/lib/api.ts tests/lib/api.test.ts
git commit -m "feat: add Yahoo Finance proxy via Cloudflare Workers + API client"
```

---

## Task 5: Dashboard Page (Portfolio List)

**Files:**
- Create: `src/pages/Dashboard.tsx`
- Create: `src/components/PortfolioCard.tsx`
- Create: `src/components/EmptyState.tsx`
- Create: `tests/components/PortfolioCard.test.tsx`
- Create: `tests/pages/Dashboard.test.tsx`

> **For Claude:** Use /ui-ux-pro-max skill for page design and styling.

**Step 1: Write failing tests for PortfolioCard**

Create `tests/components/PortfolioCard.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { PortfolioCard } from '../../src/components/PortfolioCard'
import type { Portfolio } from '../../src/types'

const mockPortfolio: Portfolio = {
  id: '1',
  name: '미국 대형주 60/40',
  description: 'AAPL + SPY',
  assets: [
    { symbol: 'AAPL', name: 'Apple Inc.', market: 'US', weight: 40 },
    { symbol: 'SPY', name: 'SPDR S&P 500', market: 'US', weight: 60 },
  ],
  rebalancing: 'quarterly',
  backtestPeriod: { startDate: '2020-01-01', endDate: '2025-12-31' },
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('PortfolioCard', () => {
  it('renders portfolio name', () => {
    renderWithRouter(<PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />)
    expect(screen.getByText('미국 대형주 60/40')).toBeInTheDocument()
  })

  it('renders asset symbols with weights', () => {
    renderWithRouter(<PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />)
    expect(screen.getByText(/AAPL/)).toBeInTheDocument()
    expect(screen.getByText(/SPY/)).toBeInTheDocument()
  })

  it('renders rebalancing type', () => {
    renderWithRouter(<PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />)
    expect(screen.getByText(/분기/)).toBeInTheDocument()
  })

  it('calls onDelete when delete button clicked', async () => {
    const onDelete = vi.fn()
    renderWithRouter(<PortfolioCard portfolio={mockPortfolio} onDelete={onDelete} />)
    await userEvent.click(screen.getByRole('button', { name: /삭제/ }))
    expect(onDelete).toHaveBeenCalledWith('1')
  })

  it('links to portfolio detail page', () => {
    renderWithRouter(<PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />)
    const link = screen.getByRole('link', { name: /보기/ })
    expect(link).toHaveAttribute('href', '/portfolio/1')
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/components/PortfolioCard.test.tsx
```

Expected: FAIL — module not found

**Step 3: Implement PortfolioCard, EmptyState, and Dashboard**

> Use /ui-ux-pro-max skill here for polished UI with dark theme, proper typography, and financial app aesthetics.

Implement components with:
- `PortfolioCard`: Card with name, asset badges, rebalancing info, view/edit/delete actions
- `EmptyState`: Friendly empty state with CTA button
- `Dashboard`: Grid layout showing all portfolio cards, "새 전략 만들기" button in header

**Step 4: Run tests to verify they pass**

```bash
npx vitest run tests/components/ tests/pages/Dashboard.test.tsx
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/pages/Dashboard.tsx src/components/PortfolioCard.tsx src/components/EmptyState.tsx
git add tests/components/PortfolioCard.test.tsx tests/pages/Dashboard.test.tsx
git commit -m "feat: add dashboard page with portfolio card grid"
```

---

## Task 6: Portfolio Form (Create / Edit)

**Files:**
- Create: `src/pages/PortfolioNew.tsx`
- Create: `src/pages/PortfolioEdit.tsx`
- Create: `src/components/PortfolioForm.tsx`
- Create: `src/hooks/usePortfolioForm.ts`
- Create: `tests/hooks/usePortfolioForm.test.ts`
- Create: `tests/components/PortfolioForm.test.tsx`

> **For Claude:** Use /ui-ux-pro-max skill for form design and styling.

**Step 1: Write failing tests for usePortfolioForm hook**

Create `tests/hooks/usePortfolioForm.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePortfolioForm } from '../../src/hooks/usePortfolioForm'

describe('usePortfolioForm', () => {
  it('initializes with empty form', () => {
    const { result } = renderHook(() => usePortfolioForm())
    expect(result.current.form.name).toBe('')
    expect(result.current.form.assets).toEqual([])
    expect(result.current.form.rebalancing).toBe('quarterly')
  })

  it('updates name', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() => result.current.setName('My Strategy'))
    expect(result.current.form.name).toBe('My Strategy')
  })

  it('adds an asset', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple Inc.',
        market: 'US',
        weight: 50,
      })
    )
    expect(result.current.form.assets).toHaveLength(1)
    expect(result.current.form.assets[0].symbol).toBe('AAPL')
  })

  it('removes an asset', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 100,
      })
    )
    act(() => result.current.removeAsset('AAPL'))
    expect(result.current.form.assets).toHaveLength(0)
  })

  it('updates asset weight', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 50,
      })
    )
    act(() => result.current.updateAssetWeight('AAPL', 70))
    expect(result.current.form.assets[0].weight).toBe(70)
  })

  it('validates total weight equals 100', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 60,
      })
    )
    expect(result.current.isValid).toBe(false)
    act(() =>
      result.current.addAsset({
        symbol: 'SPY',
        name: 'SPY',
        market: 'US',
        weight: 40,
      })
    )
    expect(result.current.isValid).toBe(true)
  })

  it('validates name is not empty', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 100,
      })
    )
    expect(result.current.isValid).toBe(false) // name empty
    act(() => result.current.setName('Strategy'))
    expect(result.current.isValid).toBe(true)
  })

  it('initializes with existing portfolio data', () => {
    const initial = {
      name: 'Existing',
      description: 'Desc',
      assets: [{ symbol: 'AAPL', name: 'Apple', market: 'US' as const, weight: 100 }],
      rebalancing: 'monthly' as const,
      backtestPeriod: { startDate: '2020-01-01', endDate: '2025-12-31' },
    }
    const { result } = renderHook(() => usePortfolioForm(initial))
    expect(result.current.form.name).toBe('Existing')
    expect(result.current.form.assets).toHaveLength(1)
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/hooks/usePortfolioForm.test.ts
```

Expected: FAIL

**Step 3: Implement usePortfolioForm hook**

Create `src/hooks/usePortfolioForm.ts` with immutable state updates for all operations.

**Step 4: Implement PortfolioForm, PortfolioNew, PortfolioEdit pages**

> Use /ui-ux-pro-max skill for form design:
> - Symbol search input with market selector (US/KR)
> - Weight slider or input with real-time total indicator
> - Rebalancing radio buttons
> - Date pickers for backtest period
> - Visual weight bar chart

**Step 5: Run all tests**

```bash
npx vitest run
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/pages/PortfolioNew.tsx src/pages/PortfolioEdit.tsx src/components/PortfolioForm.tsx
git add src/hooks/usePortfolioForm.ts tests/hooks/usePortfolioForm.test.ts tests/components/PortfolioForm.test.tsx
git commit -m "feat: add portfolio create/edit form with validation"
```

---

## Task 7: Backtest Result Page (Charts + Metrics)

**Files:**
- Create: `src/pages/PortfolioDetail.tsx`
- Create: `src/components/MetricCard.tsx`
- Create: `src/components/AssetBadge.tsx`
- Create: `src/components/PortfolioChart.tsx`
- Create: `src/components/DrawdownChart.tsx`
- Create: `src/hooks/useBacktest.ts`
- Create: `tests/hooks/useBacktest.test.ts`
- Create: `tests/components/MetricCard.test.tsx`

> **For Claude:** Use /ui-ux-pro-max skill for page design and styling.

**Step 1: Write failing tests for useBacktest hook**

Create `tests/hooks/useBacktest.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useBacktest } from '../../src/hooks/useBacktest'
import type { Portfolio } from '../../src/types'

vi.mock('../../src/lib/api', () => ({
  fetchStockData: vi.fn(),
}))

vi.mock('../../src/lib/backtest-engine', () => ({
  runBacktest: vi.fn(),
}))

const mockPortfolio: Portfolio = {
  id: '1',
  name: 'Test',
  description: '',
  assets: [{ symbol: 'AAPL', name: 'Apple', market: 'US', weight: 100 }],
  rebalancing: 'none',
  backtestPeriod: { startDate: '2024-01-01', endDate: '2024-12-31' },
  createdAt: '',
  updatedAt: '',
}

describe('useBacktest', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('starts with loading state', () => {
    const { fetchStockData } = require('../../src/lib/api')
    fetchStockData.mockReturnValue(new Promise(() => {})) // never resolves
    const { result } = renderHook(() => useBacktest(mockPortfolio))
    expect(result.current.isLoading).toBe(true)
    expect(result.current.result).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('returns result on success', async () => {
    const { fetchStockData } = require('../../src/lib/api')
    const { runBacktest } = require('../../src/lib/backtest-engine')
    const mockResult = { portfolioId: '1', totalReturn: 10 }

    fetchStockData.mockResolvedValue({ AAPL: [] })
    runBacktest.mockReturnValue(mockResult)

    const { result } = renderHook(() => useBacktest(mockPortfolio))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.result).toEqual(mockResult)
    expect(result.current.error).toBeNull()
  })

  it('returns error on failure', async () => {
    const { fetchStockData } = require('../../src/lib/api')
    fetchStockData.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useBacktest(mockPortfolio))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.result).toBeNull()
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/hooks/useBacktest.test.ts
```

Expected: FAIL

**Step 3: Implement useBacktest hook**

Create `src/hooks/useBacktest.ts`:
- Fetch stock data via API client
- Run backtest engine
- Return `{ isLoading, result, error }` state

**Step 4: Implement chart components**

> Use /ui-ux-pro-max skill for chart presentation:
> - `PortfolioChart`: TradingView Lightweight Charts area chart for portfolio value timeline
> - `DrawdownChart`: Lightweight Charts area chart (red) for drawdown
> - `MetricCard`: Stat card with label, value, color (green/red based on +/-)
> - `AssetBadge`: Colored badge showing symbol + weight %

**Step 5: Implement PortfolioDetail page**

Layout order:
1. Header (name + edit/delete buttons)
2. AssetBadge row
3. MetricCard grid (CAGR, MaxDrawdown, Sharpe, Volatility)
4. PortfolioChart (full width)
5. DrawdownChart (full width)

**Step 6: Run all tests**

```bash
npx vitest run
```

Expected: All tests PASS

**Step 7: Commit**

```bash
git add src/pages/PortfolioDetail.tsx src/components/MetricCard.tsx src/components/AssetBadge.tsx
git add src/components/PortfolioChart.tsx src/components/DrawdownChart.tsx
git add src/hooks/useBacktest.ts tests/hooks/useBacktest.test.ts tests/components/MetricCard.test.tsx
git commit -m "feat: add backtest result page with charts and metrics"
```

---

## Task 8: Integration, Routing & Polish

**Files:**
- Modify: `src/App.tsx`
- Create: `src/components/Layout.tsx`
- Create: `src/components/ConfirmDialog.tsx`
- Modify: `index.html` (title, meta tags)

> **For Claude:** Use /ui-ux-pro-max skill for layout and polish.

**Step 1: Wire up App routing with all pages**

Update `src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { PortfolioNew } from './pages/PortfolioNew'
import { PortfolioDetail } from './pages/PortfolioDetail'
import { PortfolioEdit } from './pages/PortfolioEdit'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/portfolio/new" element={<PortfolioNew />} />
          <Route path="/portfolio/:id" element={<PortfolioDetail />} />
          <Route path="/portfolio/:id/edit" element={<PortfolioEdit />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
```

**Step 2: Implement Layout with navigation header**

- App logo/title "BacktestLab"
- Dark theme with financial app aesthetic
- Responsive container

**Step 3: Add delete confirmation dialog**

- `ConfirmDialog` component with cancel/confirm actions
- Used in Dashboard and PortfolioDetail for delete operations

**Step 4: Update index.html**

```html
<title>BacktestLab - 주식 백테스트</title>
<meta name="description" content="한국/미국 주식 자산 배분 백테스트" />
```

**Step 5: Run full test suite**

```bash
npx vitest run --coverage
```

Expected: All tests PASS, coverage > 80%

**Step 6: Test build**

```bash
npm run build
```

Expected: Build succeeds

**Step 7: Commit**

```bash
git add .
git commit -m "feat: integrate routing, layout, and polish"
```

---

## Task 9: Final QA & Deployment Setup

**Files:**
- Modify: `package.json` (scripts)
- Create: `.github/workflows/deploy.yml` (optional)

**Step 1: Add production scripts to package.json**

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "wrangler pages dev dist",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "lint": "eslint .",
    "deploy": "npm run build && wrangler pages deploy dist"
  }
}
```

**Step 2: Run full QA**

```bash
npm run lint
npm run test:coverage
npm run build
npm run preview
```

Expected: All pass, coverage > 80%

**Step 3: Manual smoke test**

1. Open localhost → Dashboard shows empty state
2. Create new strategy → Form works, saves to localStorage
3. View strategy → Backtest runs, charts render
4. Edit strategy → Prefilled form, saves changes
5. Delete strategy → Confirm dialog, removes from list

**Step 4: Update apps/README.md**

Add backtest-lab entry to the project table.

**Step 5: Final commit**

```bash
git add .
git commit -m "chore: add deployment config and QA checklist"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Project scaffolding | Setup only |
| 2 | Types + LocalStorage CRUD | 8 tests |
| 3 | Backtest engine | 10 tests |
| 4 | Workers API + client | 4 tests |
| 5 | Dashboard page | ~5 tests |
| 6 | Portfolio form | ~8 tests |
| 7 | Backtest result page | ~3 tests |
| 8 | Integration & polish | Build verification |
| 9 | QA & deployment | Smoke test |

**Total estimated tests: ~38+**
**Target coverage: 80%+**
