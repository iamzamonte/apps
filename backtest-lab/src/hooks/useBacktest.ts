import { useState, useEffect, useCallback } from 'react'
import { fetchStockData } from '../lib/api'
import { runBacktest } from '../lib/backtest-engine'
import type { Portfolio, BacktestResult } from '../types'

interface UseBacktestReturn {
  readonly isLoading: boolean
  readonly result: BacktestResult | null
  readonly error: string | null
  readonly refetch: () => Promise<void>
}

export function useBacktest(portfolio: Portfolio): UseBacktestReturn {
  const [isLoading, setIsLoading] = useState(true)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const execute = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const symbols = portfolio.assets.map((a) => a.symbol)
      const stockData = await fetchStockData(
        symbols,
        portfolio.backtestPeriod.startDate,
        portfolio.backtestPeriod.endDate
      )
      const backtestResult = runBacktest(portfolio, stockData)
      setResult(backtestResult)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'An unknown error occurred'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [portfolio])

  useEffect(() => {
    void execute()
  }, [execute])

  return {
    isLoading,
    result,
    error,
    refetch: execute,
  }
}
