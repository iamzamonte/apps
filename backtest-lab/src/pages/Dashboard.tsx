import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getPortfolios, deletePortfolio } from '../lib/storage'
import { PortfolioCard } from '../components/PortfolioCard'
import { EmptyState } from '../components/EmptyState'
import type { Portfolio } from '../types'
import styles from './Dashboard.module.css'

export function Dashboard() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>(() =>
    getPortfolios()
  )

  const handleDelete = useCallback((id: string) => {
    const confirmed = window.confirm('이 전략을 삭제하시겠습니까?')
    if (!confirmed) return

    deletePortfolio(id)
    setPortfolios((prev) => prev.filter((p) => p.id !== id))
  }, [])

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>BacktestLab</h1>
        <Link to="/portfolio/new" className={styles.newButton}>
          + 새 전략 만들기
        </Link>
      </div>
      {portfolios.length === 0 ? (
        <EmptyState />
      ) : (
        <div className={styles.grid}>
          {portfolios.map((portfolio) => (
            <PortfolioCard
              key={portfolio.id}
              portfolio={portfolio}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}
