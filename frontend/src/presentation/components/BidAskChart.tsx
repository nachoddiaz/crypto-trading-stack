// TradingView Lightweight Charts - Bid/Ask Line Chart Component
import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts'
import { BidAskTick } from '../../domain/types'

interface Props {
    ticks: BidAskTick[]
}

export default function BidAskChart({ ticks }: Props) {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const bidSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
    const askSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)

    useEffect(() => {
        if (!containerRef.current) return

        const chart = createChart(containerRef.current, {
            layout: {
                background: { color: '#161b22' },
                textColor: '#c9d1d9',
            },
            grid: {
                vertLines: { color: '#21262d' },
                horzLines: { color: '#21262d' },
            },
            width: containerRef.current.clientWidth,
            height: 300,
            timeScale: {
                timeVisible: true,
                secondsVisible: true,
            },
        })

        const bidSeries = chart.addLineSeries({
            color: '#3fb950',
            lineWidth: 2,
            title: 'Bid',
        })

        const askSeries = chart.addLineSeries({
            color: '#f85149',
            lineWidth: 2,
            title: 'Ask',
        })

        chartRef.current = chart
        bidSeriesRef.current = bidSeries
        askSeriesRef.current = askSeries

        return () => {
            chart.remove()
        }
    }, [])

    useEffect(() => {
        if (!bidSeriesRef.current || !askSeriesRef.current || ticks.length === 0) return

        // Eliminar duplicados y ordenar
        const seen = new Set<number>()
        const processedTicks = ticks
            .map(t => ({
                time: Math.floor(t.timestamp) as Time,
                bid: t.bid_price,
                ask: t.ask_price,
            }))
            .sort((a, b) => (a.time as number) - (b.time as number))
            .filter(t => {
                const time = t.time as number
                if (seen.has(time)) return false
                seen.add(time)
                return true
            })

        const bidData: LineData<Time>[] = processedTicks.map(t => ({
            time: t.time,
            value: t.bid,
        }))

        const askData: LineData<Time>[] = processedTicks.map(t => ({
            time: t.time,
            value: t.ask,
        }))

        if (bidData.length > 0) {
            bidSeriesRef.current.setData(bidData)
            askSeriesRef.current.setData(askData)
            chartRef.current?.timeScale().fitContent()
        }
    }, [ticks])

    useEffect(() => {
        const handleResize = () => {
            if (containerRef.current && chartRef.current) {
                chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
            }
        }

        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    return <div ref={containerRef} style={{ width: '100%', height: '300px' }} />
}
