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

// Stock A: 100 -> 110 (+10%)
// Stock B: 200 -> 220 (+10%)
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

describe('runBacktest edge cases', () => {
  it('handles empty stock data gracefully', () => {
    const result = runBacktest(mockPortfolio, {})
    expect(result.timeline).toEqual([])
    expect(result.totalReturn).toBe(0)
  })

  it('handles single data point', () => {
    const singleDay: StockData = {
      A: [{ date: '2024-01-01', close: 100 }],
      B: [{ date: '2024-01-01', close: 200 }],
    }
    const result = runBacktest(mockPortfolio, singleDay)
    expect(result.totalReturn).toBe(0)
  })
})
