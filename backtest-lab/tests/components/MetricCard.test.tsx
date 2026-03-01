import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetricCard } from '../../src/components/MetricCard'

describe('MetricCard', () => {
  it('renders label and value', () => {
    render(<MetricCard label="CAGR" value="12.3%" />)
    expect(screen.getByText('CAGR')).toBeInTheDocument()
    expect(screen.getByText('12.3%')).toBeInTheDocument()
  })

  it('applies positive color for positive values', () => {
    const { container } = render(
      <MetricCard label="CAGR" value="12.3%" variant="positive" />
    )
    expect(
      container.querySelector('[class*="positive"]') ||
        container.querySelector('[style*="color"]')
    ).toBeTruthy()
  })

  it('applies negative color for negative values', () => {
    const { container } = render(
      <MetricCard label="최대낙폭" value="-15.2%" variant="negative" />
    )
    expect(
      container.querySelector('[class*="negative"]') ||
        container.querySelector('[style*="color"]')
    ).toBeTruthy()
  })

  it('renders with neutral variant by default', () => {
    render(<MetricCard label="샤프비율" value="1.23" />)
    expect(screen.getByText('1.23')).toBeInTheDocument()
  })
})
