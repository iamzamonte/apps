import { useNavigate } from 'react-router-dom'
import { createPortfolio } from '../lib/storage'
import { PortfolioForm } from '../components/PortfolioForm'
import type { Asset, RebalancingType, BacktestPeriod } from '../types'
import styles from './PortfolioNew.module.css'

export function PortfolioNew() {
  const navigate = useNavigate()

  const handleSubmit = (data: {
    name: string
    description: string
    assets: Asset[]
    rebalancing: RebalancingType
    backtestPeriod: BacktestPeriod
  }) => {
    const portfolio = createPortfolio(data)
    navigate(`/portfolio/${portfolio.id}`)
  }

  return (
    <div>
      <h1 className={styles.title}>새 전략 만들기</h1>
      <PortfolioForm onSubmit={handleSubmit} submitLabel="저장" />
    </div>
  )
}
