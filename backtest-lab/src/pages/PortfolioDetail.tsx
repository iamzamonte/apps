import { useParams, useNavigate, Link } from 'react-router-dom'
import { getPortfolio, deletePortfolio } from '../lib/storage'
import { useBacktest } from '../hooks/useBacktest'
import { MetricCard } from '../components/MetricCard'
import { AssetBadge } from '../components/AssetBadge'
import { PortfolioChart } from '../components/PortfolioChart'
import { DrawdownChart } from '../components/DrawdownChart'
import styles from './PortfolioDetail.module.css'

function getVariant(value: number): 'positive' | 'negative' | 'neutral' {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}

function PortfolioDetailContent({
  portfolioId,
}: {
  readonly portfolioId: string
}) {
  const navigate = useNavigate()
  const portfolio = getPortfolio(portfolioId)

  const placeholderPortfolio = portfolio ?? {
    id: portfolioId,
    name: '',
    description: '',
    assets: [],
    rebalancing: 'none' as const,
    backtestPeriod: { startDate: '2020-01-01', endDate: '2025-12-31' },
    createdAt: '',
    updatedAt: '',
  }

  const { isLoading, result, error } = useBacktest(placeholderPortfolio)

  if (!portfolio) {
    return <div className={styles.notFound}>전략을 찾을 수 없습니다.</div>
  }

  const handleDelete = () => {
    const confirmed = window.confirm('이 전략을 삭제하시겠습니까?')
    if (!confirmed) return

    deletePortfolio(portfolio.id)
    navigate('/')
  }

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>{portfolio.name}</h1>
        <Link
          to={`/portfolio/${portfolio.id}/edit`}
          className={styles.editLink}
        >
          수정
        </Link>
        <button
          type="button"
          className={styles.deleteButton}
          onClick={handleDelete}
        >
          삭제
        </button>
      </div>

      <div className={styles.badges}>
        {portfolio.assets.map((asset) => (
          <AssetBadge key={asset.symbol} asset={asset} />
        ))}
      </div>

      {isLoading && <div className={styles.loading}>백테스트 실행 중...</div>}

      {error && (
        <div className={styles.error}>오류가 발생했습니다: {error}</div>
      )}

      {result && (
        <>
          <div className={styles.metrics}>
            <MetricCard
              label="CAGR"
              value={`${String(result.annualizedReturn)}%`}
              variant={getVariant(result.annualizedReturn)}
            />
            <MetricCard
              label="최대낙폭"
              value={`${String(result.maxDrawdown)}%`}
              variant={result.maxDrawdown < 0 ? 'negative' : 'neutral'}
            />
            <MetricCard
              label="샤프비율"
              value={String(result.sharpeRatio)}
              variant={getVariant(result.sharpeRatio)}
            />
            <MetricCard
              label="변동성"
              value={`${String(result.volatility)}%`}
              variant="neutral"
            />
          </div>

          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>포트폴리오 가치</h2>
            <PortfolioChart timeline={result.timeline} />
          </div>

          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>낙폭 (Drawdown)</h2>
            <DrawdownChart timeline={result.timeline} />
          </div>
        </>
      )}
    </div>
  )
}

export function PortfolioDetail() {
  const { id } = useParams<{ id: string }>()

  if (!id) {
    return <div className={styles.notFound}>전략을 찾을 수 없습니다.</div>
  }

  return <PortfolioDetailContent portfolioId={id} />
}
