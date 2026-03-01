import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { Dashboard } from '../../src/pages/Dashboard'
import * as storage from '../../src/lib/storage'

vi.mock('../../src/lib/storage')

const mockPortfolio = {
  id: '1',
  name: '미국 대형주 60/40',
  description: 'AAPL + SPY',
  assets: [
    { symbol: 'AAPL', name: 'Apple Inc.', market: 'US' as const, weight: 40 },
    { symbol: 'SPY', name: 'SPDR S&P 500', market: 'US' as const, weight: 60 },
  ],
  rebalancing: 'quarterly' as const,
  backtestPeriod: { startDate: '2020-01-01', endDate: '2025-12-31' },
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders header with title', () => {
    vi.mocked(storage.getPortfolios).mockReturnValue([])
    renderWithRouter(<Dashboard />)
    expect(screen.getByText('BacktestLab')).toBeInTheDocument()
  })

  it('renders new strategy button', () => {
    vi.mocked(storage.getPortfolios).mockReturnValue([])
    renderWithRouter(<Dashboard />)
    const links = screen.getAllByRole('link', { name: /새 전략 만들기/ })
    expect(links.length).toBeGreaterThanOrEqual(1)
    expect(links[0]).toHaveAttribute('href', '/portfolio/new')
  })

  it('shows empty state when no portfolios', () => {
    vi.mocked(storage.getPortfolios).mockReturnValue([])
    renderWithRouter(<Dashboard />)
    expect(screen.getByText('아직 전략이 없습니다')).toBeInTheDocument()
  })

  it('shows portfolio cards when portfolios exist', () => {
    vi.mocked(storage.getPortfolios).mockReturnValue([mockPortfolio])
    renderWithRouter(<Dashboard />)
    expect(screen.getByText('미국 대형주 60/40')).toBeInTheDocument()
  })

  it('deletes portfolio after confirmation', async () => {
    vi.mocked(storage.getPortfolios).mockReturnValue([mockPortfolio])
    vi.mocked(storage.deletePortfolio).mockReturnValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderWithRouter(<Dashboard />)
    await userEvent.click(screen.getByRole('button', { name: /삭제/ }))

    expect(window.confirm).toHaveBeenCalled()
    expect(storage.deletePortfolio).toHaveBeenCalledWith('1')
  })

  it('does not delete portfolio when confirmation cancelled', async () => {
    vi.mocked(storage.getPortfolios).mockReturnValue([mockPortfolio])
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    renderWithRouter(<Dashboard />)
    await userEvent.click(screen.getByRole('button', { name: /삭제/ }))

    expect(storage.deletePortfolio).not.toHaveBeenCalled()
  })
})
