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
