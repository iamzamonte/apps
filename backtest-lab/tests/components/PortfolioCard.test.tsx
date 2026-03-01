import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { PortfolioCard } from '../../src/components/PortfolioCard'

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

describe('PortfolioCard', () => {
  it('renders portfolio name', () => {
    renderWithRouter(
      <PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />
    )
    expect(screen.getByText('미국 대형주 60/40')).toBeInTheDocument()
  })

  it('renders asset symbols with weights', () => {
    renderWithRouter(
      <PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />
    )
    expect(screen.getByText(/AAPL/)).toBeInTheDocument()
    expect(screen.getByText(/SPY/)).toBeInTheDocument()
  })

  it('calls onDelete when delete button clicked', async () => {
    const onDelete = vi.fn()
    renderWithRouter(
      <PortfolioCard portfolio={mockPortfolio} onDelete={onDelete} />
    )
    await userEvent.click(screen.getByRole('button', { name: /삭제/ }))
    expect(onDelete).toHaveBeenCalledWith('1')
  })

  it('links to portfolio detail page', () => {
    renderWithRouter(
      <PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />
    )
    const link = screen.getByRole('link', { name: /보기/ })
    expect(link).toHaveAttribute('href', '/portfolio/1')
  })

  it('links to portfolio edit page', () => {
    renderWithRouter(
      <PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />
    )
    const link = screen.getByRole('link', { name: /수정/ })
    expect(link).toHaveAttribute('href', '/portfolio/1/edit')
  })

  it('displays market flag for US assets', () => {
    renderWithRouter(
      <PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />
    )
    expect(screen.getAllByText(/\u{1F1FA}\u{1F1F8}/u)).toHaveLength(2)
  })

  it('displays rebalancing type', () => {
    renderWithRouter(
      <PortfolioCard portfolio={mockPortfolio} onDelete={vi.fn()} />
    )
    expect(screen.getByText(/분기/)).toBeInTheDocument()
  })

  it('displays KR flag for Korean market assets', () => {
    const krPortfolio = {
      ...mockPortfolio,
      assets: [
        {
          symbol: '005930.KS',
          name: '삼성전자',
          market: 'KR' as const,
          weight: 100,
        },
      ],
    }
    renderWithRouter(
      <PortfolioCard portfolio={krPortfolio} onDelete={vi.fn()} />
    )
    expect(screen.getByText(/\u{1F1F0}\u{1F1F7}/u)).toBeInTheDocument()
  })
})
