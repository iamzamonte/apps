import { Link } from 'react-router-dom'
import styles from './EmptyState.module.css'

export function EmptyState() {
  return (
    <div className={styles.container}>
      <h2 className={styles.title}>아직 전략이 없습니다</h2>
      <p className={styles.subtitle}>
        첫 번째 포트폴리오 전략을 만들어보세요
      </p>
      <Link to="/portfolio/new" className={styles.ctaButton}>
        + 새 전략 만들기
      </Link>
    </div>
  )
}
