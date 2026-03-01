import styles from './MetricCard.module.css'

interface MetricCardProps {
  readonly label: string
  readonly value: string
  readonly variant?: 'positive' | 'negative' | 'neutral'
}

export function MetricCard({
  label,
  value,
  variant = 'neutral',
}: MetricCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.label}>{label}</div>
      <div className={`${styles.value} ${styles[variant]}`}>{value}</div>
    </div>
  )
}
