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
