import { useParams, useNavigate } from 'react-router-dom'
import { getPortfolio, updatePortfolio } from '../lib/storage'
import { PortfolioForm } from '../components/PortfolioForm'
import type { Asset, RebalancingType, BacktestPeriod } from '../types'
import styles from './PortfolioEdit.module.css'

export function PortfolioEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const portfolio = id ? getPortfolio(id) : undefined

  if (!portfolio) {
    return <div className={styles.error}>전략을 찾을 수 없습니다.</div>
  }

  const handleSubmit = (data: {
    name: string
    description: string
    assets: Asset[]
    rebalancing: RebalancingType
    backtestPeriod: BacktestPeriod
  }) => {
    updatePortfolio(portfolio.id, data)
    navigate(`/portfolio/${portfolio.id}`)
  }

  return (
    <div>
      <h1 className={styles.title}>전략 수정</h1>
      <PortfolioForm
        initialData={{
          name: portfolio.name,
          description: portfolio.description,
          assets: portfolio.assets,
          rebalancing: portfolio.rebalancing,
          backtestPeriod: portfolio.backtestPeriod,
        }}
        onSubmit={handleSubmit}
        submitLabel="저장"
      />
    </div>
  )
}
