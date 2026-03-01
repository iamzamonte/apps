import type { FormEvent } from 'react'
import type { Asset, RebalancingType, BacktestPeriod } from '../types'
import {
  usePortfolioForm,
} from '../hooks/usePortfolioForm'
import styles from './PortfolioForm.module.css'

interface PortfolioFormProps {
  readonly initialData?: {
    readonly name: string
    readonly description: string
    readonly assets: readonly Asset[]
    readonly rebalancing: RebalancingType
    readonly backtestPeriod: BacktestPeriod
  }
  readonly onSubmit: (data: {
    name: string
    description: string
    assets: Asset[]
    rebalancing: RebalancingType
    backtestPeriod: BacktestPeriod
  }) => void
  readonly submitLabel?: string
}

const REBALANCING_OPTIONS: readonly {
  readonly value: RebalancingType
  readonly label: string
}[] = [
  { value: 'none', label: '없음' },
  { value: 'monthly', label: '매월' },
  { value: 'quarterly', label: '분기' },
  { value: 'semi-annually', label: '반기' },
  { value: 'annually', label: '연간' },
]

export function PortfolioForm({
  initialData,
  onSubmit,
  submitLabel = '저장',
}: PortfolioFormProps) {
  const {
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
  } = usePortfolioForm(initialData)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!isValid) return

    onSubmit({
      name: form.name,
      description: form.description,
      assets: [...form.assets],
      rebalancing: form.rebalancing,
      backtestPeriod: { ...form.backtestPeriod },
    })
  }

  const handleAddAsset = () => {
    addAsset({ symbol: '', name: '', market: 'US', weight: 0 })
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.fieldGroup}>
        <label className={styles.label} htmlFor="strategy-name">
          전략 이름
        </label>
        <input
          id="strategy-name"
          className={styles.input}
          type="text"
          value={form.name}
          onChange={(e) => setName(e.target.value)}
          placeholder="예: 미국 대형주 60/40"
        />
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.label} htmlFor="strategy-desc">
          설명
        </label>
        <textarea
          id="strategy-desc"
          className={styles.textarea}
          value={form.description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="전략에 대한 설명을 입력하세요"
        />
      </div>

      <div className={styles.fieldGroup}>
        <span className={styles.label}>종목</span>
        <div className={styles.assetList}>
          {form.assets.map((asset, index) => (
            <div key={`asset-${String(index)}`} className={styles.assetRow}>
              <input
                className={`${styles.assetInput} ${styles.symbolInput}`}
                type="text"
                value={asset.symbol}
                placeholder="심볼"
                readOnly
                aria-label={`종목 ${String(index + 1)} 심볼`}
              />
              <input
                className={`${styles.assetInput} ${styles.nameInput}`}
                type="text"
                value={asset.name}
                placeholder="종목명"
                readOnly
                aria-label={`종목 ${String(index + 1)} 이름`}
              />
              <select
                className={styles.marketSelect}
                value={asset.market}
                disabled
                aria-label={`종목 ${String(index + 1)} 시장`}
              >
                <option value="US">US</option>
                <option value="KR">KR</option>
              </select>
              <input
                className={`${styles.assetInput} ${styles.weightInput}`}
                type="number"
                value={asset.weight}
                onChange={(e) =>
                  updateAssetWeight(asset.symbol, Number(e.target.value))
                }
                placeholder="비중"
                min={0}
                max={100}
                aria-label={`종목 ${String(index + 1)} 비중`}
              />
              <span className={styles.label}>%</span>
              <button
                type="button"
                className={styles.removeButton}
                onClick={() => removeAsset(asset.symbol)}
                aria-label={`종목 ${asset.symbol} 삭제`}
              >
                삭제
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          className={styles.addButton}
          onClick={handleAddAsset}
        >
          + 종목 추가
        </button>
        <div
          className={`${styles.weightTotal} ${totalWeight === 100 ? styles.weightValid : styles.weightInvalid}`}
        >
          총 비중: {totalWeight}%
        </div>
      </div>

      <div className={styles.fieldGroup}>
        <span className={styles.label}>리밸런싱</span>
        <div className={styles.radioGroup}>
          {REBALANCING_OPTIONS.map((option) => (
            <label key={option.value} className={styles.radioLabel}>
              <input
                type="radio"
                name="rebalancing"
                value={option.value}
                checked={form.rebalancing === option.value}
                onChange={() => setRebalancing(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

      <div className={styles.fieldGroup}>
        <span className={styles.label}>백테스트 기간</span>
        <div className={styles.dateGroup}>
          <input
            className={styles.dateInput}
            type="date"
            value={form.backtestPeriod.startDate}
            onChange={(e) =>
              setBacktestPeriod({
                ...form.backtestPeriod,
                startDate: e.target.value,
              })
            }
            aria-label="시작일"
          />
          <span className={styles.dateSeparator}>~</span>
          <input
            className={styles.dateInput}
            type="date"
            value={form.backtestPeriod.endDate}
            onChange={(e) =>
              setBacktestPeriod({
                ...form.backtestPeriod,
                endDate: e.target.value,
              })
            }
            aria-label="종료일"
          />
        </div>
      </div>

      <button
        type="submit"
        className={styles.submitButton}
        disabled={!isValid}
      >
        {submitLabel}
      </button>
    </form>
  )
}
