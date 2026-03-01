import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePortfolioForm } from '../../src/hooks/usePortfolioForm'

describe('usePortfolioForm', () => {
  it('initializes with empty form', () => {
    const { result } = renderHook(() => usePortfolioForm())
    expect(result.current.form.name).toBe('')
    expect(result.current.form.assets).toEqual([])
    expect(result.current.form.rebalancing).toBe('quarterly')
  })

  it('updates name', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() => result.current.setName('My Strategy'))
    expect(result.current.form.name).toBe('My Strategy')
  })

  it('updates description', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() => result.current.setDescription('A test description'))
    expect(result.current.form.description).toBe('A test description')
  })

  it('adds an asset', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple Inc.',
        market: 'US',
        weight: 50,
      })
    )
    expect(result.current.form.assets).toHaveLength(1)
  })

  it('removes an asset', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 100,
      })
    )
    act(() => result.current.removeAsset('AAPL'))
    expect(result.current.form.assets).toHaveLength(0)
  })

  it('updates asset weight', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 50,
      })
    )
    act(() => result.current.updateAssetWeight('AAPL', 70))
    expect(result.current.form.assets[0]?.weight).toBe(70)
  })

  it('validates total weight equals 100', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() => result.current.setName('Test'))
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 60,
      })
    )
    expect(result.current.isValid).toBe(false)
    act(() =>
      result.current.addAsset({
        symbol: 'SPY',
        name: 'SPY',
        market: 'US',
        weight: 40,
      })
    )
    expect(result.current.isValid).toBe(true)
  })

  it('validates name is not empty', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 100,
      })
    )
    expect(result.current.isValid).toBe(false)
    act(() => result.current.setName('Strategy'))
    expect(result.current.isValid).toBe(true)
  })

  it('initializes with existing portfolio data', () => {
    const initial = {
      name: 'Existing',
      description: 'Desc',
      assets: [
        { symbol: 'AAPL', name: 'Apple', market: 'US' as const, weight: 100 },
      ],
      rebalancing: 'monthly' as const,
      backtestPeriod: { startDate: '2020-01-01', endDate: '2025-12-31' },
    }
    const { result } = renderHook(() => usePortfolioForm(initial))
    expect(result.current.form.name).toBe('Existing')
    expect(result.current.form.assets).toHaveLength(1)
    expect(result.current.form.rebalancing).toBe('monthly')
  })

  it('sets rebalancing type', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() => result.current.setRebalancing('annually'))
    expect(result.current.form.rebalancing).toBe('annually')
  })

  it('sets backtest period', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.setBacktestPeriod({
        startDate: '2022-01-01',
        endDate: '2024-12-31',
      })
    )
    expect(result.current.form.backtestPeriod.startDate).toBe('2022-01-01')
    expect(result.current.form.backtestPeriod.endDate).toBe('2024-12-31')
  })

  it('computes total weight', () => {
    const { result } = renderHook(() => usePortfolioForm())
    act(() =>
      result.current.addAsset({
        symbol: 'AAPL',
        name: 'Apple',
        market: 'US',
        weight: 40,
      })
    )
    act(() =>
      result.current.addAsset({
        symbol: 'SPY',
        name: 'SPY',
        market: 'US',
        weight: 60,
      })
    )
    expect(result.current.totalWeight).toBe(100)
  })
})
