import { Link } from 'react-router-dom'
import type { Portfolio, RebalancingType } from '../types'
import styles from './PortfolioCard.module.css'

interface PortfolioCardProps {
  readonly portfolio: Portfolio
  readonly onDelete: (id: string) => void
}

const MARKET_FLAGS: Record<string, string> = {
  US: '\u{1F1FA}\u{1F1F8}',
  KR: '\u{1F1F0}\u{1F1F7}',
}

const REBALANCING_LABELS: Record<RebalancingType, string> = {
  none: '없음',
  monthly: '매월',
  quarterly: '분기',
  'semi-annually': '반기',
  annually: '연간',
}

export function PortfolioCard({ portfolio, onDelete }: PortfolioCardProps) {
  const handleDelete = () => {
    onDelete(portfolio.id)
  }

  return (
    <div className={styles.card}>
      <div className={styles.name}>{portfolio.name}</div>
      <div className={styles.assets}>
        {portfolio.assets.map((asset) => (
          <span key={asset.symbol} className={styles.badge}>
            {MARKET_FLAGS[asset.market] ?? ''} {asset.symbol} {asset.weight}%
          </span>
        ))}
      </div>
      <div className={styles.rebalancing}>
        리밸런싱: {REBALANCING_LABELS[portfolio.rebalancing]}
      </div>
      <div className={styles.actions}>
        <Link to={`/portfolio/${portfolio.id}`} className={styles.actionLink}>
          보기
        </Link>
        <Link
          to={`/portfolio/${portfolio.id}/edit`}
          className={styles.actionLink}
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
    </div>
  )
}
