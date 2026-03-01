import { useState, useMemo, useCallback } from 'react'
import type { Asset, RebalancingType, BacktestPeriod } from '../types'

interface PortfolioFormData {
  readonly name: string
  readonly description: string
  readonly assets: readonly Asset[]
  readonly rebalancing: RebalancingType
  readonly backtestPeriod: BacktestPeriod
}

interface PortfolioFormInitial {
  readonly name?: string
  readonly description?: string
  readonly assets?: readonly Asset[]
  readonly rebalancing?: RebalancingType
  readonly backtestPeriod?: BacktestPeriod
}

interface UsePortfolioFormReturn {
  readonly form: PortfolioFormData
  readonly isValid: boolean
  readonly totalWeight: number
  readonly setName: (name: string) => void
  readonly setDescription: (description: string) => void
  readonly addAsset: (asset: Asset) => void
  readonly removeAsset: (symbol: string) => void
  readonly updateAssetWeight: (symbol: string, weight: number) => void
  readonly setRebalancing: (rebalancing: RebalancingType) => void
  readonly setBacktestPeriod: (period: BacktestPeriod) => void
}

const DEFAULT_PERIOD: BacktestPeriod = {
  startDate: '2020-01-01',
  endDate: '2025-12-31',
}

export function usePortfolioForm(
  initial?: PortfolioFormInitial
): UsePortfolioFormReturn {
  const [form, setForm] = useState<PortfolioFormData>({
    name: initial?.name ?? '',
    description: initial?.description ?? '',
    assets: initial?.assets ? [...initial.assets] : [],
    rebalancing: initial?.rebalancing ?? 'quarterly',
    backtestPeriod: initial?.backtestPeriod ?? { ...DEFAULT_PERIOD },
  })

  const totalWeight = useMemo(
    () => form.assets.reduce((sum, asset) => sum + asset.weight, 0),
    [form.assets]
  )

  const isValid = useMemo(
    () => form.name.trim() !== '' && form.assets.length > 0 && totalWeight === 100,
    [form.name, form.assets.length, totalWeight]
  )

  const setName = useCallback((name: string) => {
    setForm((prev) => ({ ...prev, name }))
  }, [])

  const setDescription = useCallback((description: string) => {
    setForm((prev) => ({ ...prev, description }))
  }, [])

  const addAsset = useCallback((asset: Asset) => {
    setForm((prev) => ({
      ...prev,
      assets: [...prev.assets, asset],
    }))
  }, [])

  const removeAsset = useCallback((symbol: string) => {
    setForm((prev) => ({
      ...prev,
      assets: prev.assets.filter((a) => a.symbol !== symbol),
    }))
  }, [])

  const updateAssetWeight = useCallback((symbol: string, weight: number) => {
    setForm((prev) => ({
      ...prev,
      assets: prev.assets.map((a) =>
        a.symbol === symbol ? { ...a, weight } : a
      ),
    }))
  }, [])

  const setRebalancing = useCallback((rebalancing: RebalancingType) => {
    setForm((prev) => ({ ...prev, rebalancing }))
  }, [])

  const setBacktestPeriod = useCallback((backtestPeriod: BacktestPeriod) => {
    setForm((prev) => ({ ...prev, backtestPeriod }))
  }, [])

  return {
    form,
    isValid,
    totalWeight,
    setName,
    setDescription,
    addAsset,
    removeAsset,
    updateAssetWeight,
    setRebalancing,
    setBacktestPeriod,
  }
}
