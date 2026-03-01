import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useBacktest } from '../../src/hooks/useBacktest'
import * as api from '../../src/lib/api'
import * as engine from '../../src/lib/backtest-engine'
import type { Portfolio } from '../../src/types'

vi.mock('../../src/lib/api')
vi.mock('../../src/lib/backtest-engine')

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
    vi.mocked(api.fetchStockData).mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useBacktest(mockPortfolio))
    expect(result.current.isLoading).toBe(true)
    expect(result.current.result).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('returns result on success', async () => {
    const mockResult = {
      portfolioId: '1',
      totalReturn: 10,
      annualizedReturn: 10,
      maxDrawdown: -5,
      sharpeRatio: 1,
      volatility: 15,
      timeline: [],
    }
    vi.mocked(api.fetchStockData).mockResolvedValue({ AAPL: [] })
    vi.mocked(engine.runBacktest).mockReturnValue(mockResult)

    const { result } = renderHook(() => useBacktest(mockPortfolio))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.result).toEqual(mockResult)
    expect(result.current.error).toBeNull()
  })

  it('returns error on failure', async () => {
    vi.mocked(api.fetchStockData).mockRejectedValue(
      new Error('Network error')
    )

    const { result } = renderHook(() => useBacktest(mockPortfolio))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.error).toBe('Network error')
    expect(result.current.result).toBeNull()
  })

  it('calls fetchStockData with correct parameters', async () => {
    vi.mocked(api.fetchStockData).mockResolvedValue({ AAPL: [] })
    vi.mocked(engine.runBacktest).mockReturnValue({
      portfolioId: '1',
      totalReturn: 0,
      annualizedReturn: 0,
      maxDrawdown: 0,
      sharpeRatio: 0,
      volatility: 0,
      timeline: [],
    })

    renderHook(() => useBacktest(mockPortfolio))
    await waitFor(() =>
      expect(api.fetchStockData).toHaveBeenCalledWith(
        ['AAPL'],
        '2024-01-01',
        '2024-12-31'
      )
    )
  })

  it('supports refetch', async () => {
    vi.mocked(api.fetchStockData).mockResolvedValue({ AAPL: [] })
    vi.mocked(engine.runBacktest).mockReturnValue({
      portfolioId: '1',
      totalReturn: 0,
      annualizedReturn: 0,
      maxDrawdown: 0,
      sharpeRatio: 0,
      volatility: 0,
      timeline: [],
    })

    const { result } = renderHook(() => useBacktest(mockPortfolio))
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(api.fetchStockData).toHaveBeenCalledTimes(1)

    await result.current.refetch()

    expect(api.fetchStockData).toHaveBeenCalledTimes(2)
  })
})
