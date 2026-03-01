import { useEffect, useRef } from 'react'
import {
  createChart,
  type IChartApi,
  ColorType,
  AreaSeries,
} from 'lightweight-charts'
import type { TimelinePoint } from '../types'
import styles from './PortfolioChart.module.css'

interface PortfolioChartProps {
  readonly timeline: readonly TimelinePoint[]
}

export function PortfolioChart({ timeline }: PortfolioChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        vertLine: { color: '#475569' },
        horzLine: { color: '#475569' },
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
      timeScale: {
        borderColor: '#334155',
      },
    })

    chartRef.current = chart

    const series = chart.addSeries(AreaSeries, {
      topColor: 'rgba(59, 130, 246, 0.4)',
      bottomColor: 'rgba(59, 130, 246, 0.0)',
      lineColor: '#3b82f6',
      lineWidth: 2,
    })

    const data = timeline.map((point) => ({
      time: point.date as string,
      value: point.value,
    }))

    series.setData(data)
    chart.timeScale().fitContent()

    const handleResize = () => {
      if (container && chartRef.current) {
        chartRef.current.applyOptions({ width: container.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
    }
  }, [timeline])

  return <div ref={containerRef} className={styles.container} />
}
