import type { Portfolio } from '../types'

const STORAGE_KEY = 'backtest-lab-portfolios'

function readAll(): Portfolio[] {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    return JSON.parse(raw) as Portfolio[]
  } catch {
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
  const existing = portfolios.find((p) => p.id === id)
  if (!existing) throw new Error(`Portfolio not found: ${id}`)
  const updated: Portfolio = {
    ...existing,
    ...data,
    updatedAt: new Date().toISOString(),
  }
  writeAll(portfolios.map((p) => (p.id === id ? updated : p)))
  return updated
}

export function deletePortfolio(id: string): void {
  const portfolios = readAll()
  const index = portfolios.findIndex((p) => p.id === id)
  if (index === -1) throw new Error(`Portfolio not found: ${id}`)
  writeAll(portfolios.filter((p) => p.id !== id))
}
