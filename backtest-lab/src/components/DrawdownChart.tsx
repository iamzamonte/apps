import { useEffect, useRef } from 'react'
import {
  createChart,
  type IChartApi,
  ColorType,
  AreaSeries,
} from 'lightweight-charts'
import type { TimelinePoint } from '../types'
import styles from './DrawdownChart.module.css'

interface DrawdownChartProps {
  readonly timeline: readonly TimelinePoint[]
}

export function DrawdownChart({ timeline }: DrawdownChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 200,
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
      topColor: 'rgba(239, 68, 68, 0.0)',
      bottomColor: 'rgba(239, 68, 68, 0.4)',
      lineColor: '#ef4444',
      lineWidth: 2,
    })

    const data = timeline.map((point) => ({
      time: point.date as string,
      value: point.drawdown,
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
