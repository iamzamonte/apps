import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
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
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
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
    vi.advanceTimersByTime(1000)
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
