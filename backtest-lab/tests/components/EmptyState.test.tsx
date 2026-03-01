import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { EmptyState } from '../../src/components/EmptyState'

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('EmptyState', () => {
  it('renders main message', () => {
    renderWithRouter(<EmptyState />)
    expect(screen.getByText('아직 전략이 없습니다')).toBeInTheDocument()
  })

  it('renders sub-text', () => {
    renderWithRouter(<EmptyState />)
    expect(
      screen.getByText('첫 번째 포트폴리오 전략을 만들어보세요')
    ).toBeInTheDocument()
  })

  it('links to new portfolio page', () => {
    renderWithRouter(<EmptyState />)
    const link = screen.getByRole('link', { name: /새 전략 만들기/ })
    expect(link).toHaveAttribute('href', '/portfolio/new')
  })
})
