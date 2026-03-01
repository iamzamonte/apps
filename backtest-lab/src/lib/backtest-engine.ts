import type {
  Portfolio,
  StockData,
  BacktestResult,
  TimelinePoint,
} from '../types'

const INITIAL_VALUE = 10000
const RISK_FREE_RATE = 0.04
const TRADING_DAYS_PER_YEAR = 252

const REBALANCE_INTERVALS: Record<string, number> = {
  monthly: 1,
  quarterly: 3,
  'semi-annually': 6,
  annually: 12,
}

function getRebalanceDates(
  dates: readonly string[],
  rebalancing: Portfolio['rebalancing']
): Set<string> {
  if (rebalancing === 'none') return new Set()

  const monthInterval = REBALANCE_INTERVALS[rebalancing] ?? 1
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

function buildPriceLookup(
  symbols: readonly string[],
  stockData: StockData
): Record<string, Record<string, number>> {
  const lookup: Record<string, Record<string, number>> = {}

  for (const symbol of symbols) {
    const symbolLookup: Record<string, number> = {}
    const prices = stockData[symbol]
    if (prices) {
      for (const point of prices) {
        symbolLookup[point.date] = point.close
      }
    }
    lookup[symbol] = symbolLookup
  }

  return lookup
}

function getCommonDates(
  symbols: readonly string[],
  stockData: StockData
): string[] {
  const firstSymbol = symbols[0]
  if (firstSymbol === undefined) return []

  const firstSymbolPrices = stockData[firstSymbol]
  if (!firstSymbolPrices) return []

  const dateSets = symbols.map((s: string) => {
    const prices = stockData[s]
    return new Set(prices ? prices.map((d) => d.date) : [])
  })

  return firstSymbolPrices
    .map((d) => d.date)
    .filter((date: string) => dateSets.every((ds) => ds.has(date)))
    .sort()
}

function getPrice(
  priceLookup: Record<string, Record<string, number>>,
  symbol: string,
  date: string
): number {
  const symbolPrices = priceLookup[symbol]
  if (!symbolPrices) return 0
  return symbolPrices[date] ?? 0
}

function computeShares(
  symbols: readonly string[],
  weights: readonly number[],
  portfolioValue: number,
  priceLookup: Record<string, Record<string, number>>,
  date: string
): number[] {
  return symbols.map((symbol: string, i: number) => {
    const price = getPrice(priceLookup, symbol, date)
    const weight = weights[i] ?? 0
    return price > 0 ? (portfolioValue * weight) / price : 0
  })
}

function computePortfolioValue(
  symbols: readonly string[],
  shares: readonly number[],
  priceLookup: Record<string, Record<string, number>>,
  date: string
): number {
  return symbols.reduce((sum: number, symbol: string, i: number) => {
    const shareCount = shares[i] ?? 0
    return sum + shareCount * getPrice(priceLookup, symbol, date)
  }, 0)
}

function buildEmptyResult(
  portfolioId: string,
  singleDate?: string
): BacktestResult {
  const timeline: TimelinePoint[] = singleDate
    ? [{ date: singleDate, value: INITIAL_VALUE, drawdown: 0 }]
    : []

  return {
    portfolioId,
    totalReturn: 0,
    annualizedReturn: 0,
    maxDrawdown: 0,
    sharpeRatio: 0,
    volatility: 0,
    timeline,
  }
}

function computeStatistics(
  dailyReturns: readonly number[],
  finalValue: number,
  totalDays: number
): {
  totalReturn: number
  annualizedReturn: number
  volatility: number
  sharpeRatio: number
} {
  const totalReturn = ((finalValue - INITIAL_VALUE) / INITIAL_VALUE) * 100

  const years = totalDays / TRADING_DAYS_PER_YEAR
  const annualizedReturn =
    years > 0
      ? (Math.pow(finalValue / INITIAL_VALUE, 1 / years) - 1) * 100
      : 0

  const meanReturn =
    dailyReturns.reduce((sum, r) => sum + r, 0) / dailyReturns.length
  const variance =
    dailyReturns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) /
    (dailyReturns.length - 1 || 1)
  const dailyVolatility = Math.sqrt(variance)
  const volatility = dailyVolatility * Math.sqrt(TRADING_DAYS_PER_YEAR) * 100

  const sharpeRatio =
    volatility > 0
      ? (annualizedReturn - RISK_FREE_RATE * 100) / volatility
      : 0

  return {
    totalReturn: roundTo2(totalReturn),
    annualizedReturn: roundTo2(annualizedReturn),
    volatility: roundTo2(volatility),
    sharpeRatio: roundTo2(sharpeRatio),
  }
}

function roundTo2(value: number): number {
  return Math.round(value * 100) / 100
}

export function runBacktest(
  portfolio: Portfolio,
  stockData: StockData
): BacktestResult {
  const symbols = portfolio.assets.map((a) => a.symbol)
  const weights = portfolio.assets.map((a) => a.weight / 100)

  const allDates = getCommonDates(symbols, stockData)

  if (allDates.length < 2) {
    const firstDate = allDates[0]
    return buildEmptyResult(
      portfolio.id,
      firstDate
    )
  }

  const priceLookup = buildPriceLookup(symbols, stockData)
  const rebalanceDates = getRebalanceDates(allDates, portfolio.rebalancing)

  const firstDate = allDates[0] as string
  let currentShares = computeShares(
    symbols,
    weights,
    INITIAL_VALUE,
    priceLookup,
    firstDate
  )

  const timeline: TimelinePoint[] = []
  let peak = INITIAL_VALUE
  let maxDrawdown = 0
  const dailyReturns: number[] = []
  let prevValue = INITIAL_VALUE

  for (const date of allDates) {
    const portfolioValue = computePortfolioValue(
      symbols,
      currentShares,
      priceLookup,
      date
    )

    if (date !== firstDate) {
      dailyReturns.push((portfolioValue - prevValue) / prevValue)
    }
    prevValue = portfolioValue

    if (portfolioValue > peak) peak = portfolioValue
    const drawdown = ((portfolioValue - peak) / peak) * 100
    if (drawdown < maxDrawdown) maxDrawdown = drawdown

    timeline.push({
      date,
      value: roundTo2(portfolioValue),
      drawdown: roundTo2(drawdown),
    })

    if (rebalanceDates.has(date)) {
      currentShares = computeShares(
        symbols,
        weights,
        portfolioValue,
        priceLookup,
        date
      )
    }
  }

  const lastPoint = timeline[timeline.length - 1]
  const finalValue = lastPoint ? lastPoint.value : INITIAL_VALUE
  const statistics = computeStatistics(dailyReturns, finalValue, allDates.length)

  return {
    portfolioId: portfolio.id,
    maxDrawdown: roundTo2(maxDrawdown),
    timeline,
    ...statistics,
  }
}
