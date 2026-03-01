import type { Asset } from '../types'
import styles from './AssetBadge.module.css'

interface AssetBadgeProps {
  readonly asset: Asset
}

const MARKET_FLAGS: Record<string, string> = {
  US: '\u{1F1FA}\u{1F1F8}',
  KR: '\u{1F1F0}\u{1F1F7}',
}

export function AssetBadge({ asset }: AssetBadgeProps) {
  const flag = MARKET_FLAGS[asset.market] ?? ''

  return (
    <span className={styles.badge}>
      {flag} {asset.symbol} {asset.weight}%
    </span>
  )
}
