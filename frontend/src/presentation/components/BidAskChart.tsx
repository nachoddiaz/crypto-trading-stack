// TradingView Lightweight Charts - Bid/Ask Line Chart Component
import { useEffect, useRef, useMemo } from 'react'
import { createChart, IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts'
import { BidAskTick } from '../../domain/types'

interface Props {
    ticks: BidAskTick[]
}

/**
 * Calcula el número de decimales necesarios para mostrar la diferencia entre bid y ask.
 * Si bid=78444.07 y ask=78444.12, retorna 2 (difieren en el segundo decimal).
 */
function getSignificantDecimals(bid: number, ask: number): number {
    if (bid === 0 || ask === 0) return 2

    const minDecimals = 2
    const maxDecimals = 8

    for (let d = minDecimals; d <= maxDecimals; d++) {
        const factor = Math.pow(10, d)
        const bidRounded = Math.floor(bid * factor)
        const askRounded = Math.floor(ask * factor)
        if (bidRounded !== askRounded) {
            return d
        }
    }
    return maxDecimals
}

export default function BidAskChart({ ticks }: Props) {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const bidSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
    const askSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)

    // Calcular decimales significativos basado en el último tick
    const decimals = useMemo(() => {
        if (ticks.length === 0) return 2
        const lastTick = ticks[ticks.length - 1]
        return getSignificantDecimals(lastTick.bid_price, lastTick.ask_price)
    }, [ticks])

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
            localization: {
                priceFormatter: (price: number) => price.toFixed(decimals),
            },
        })

        const bidSeries = chart.addLineSeries({
            color: '#3fb950',
            lineWidth: 2,
            title: 'Bid',
            priceFormat: {
                type: 'price',
                precision: decimals,
                minMove: Math.pow(10, -decimals),
            },
        })

        const askSeries = chart.addLineSeries({
            color: '#f85149',
            lineWidth: 2,
            title: 'Ask',
            priceFormat: {
                type: 'price',
                precision: decimals,
                minMove: Math.pow(10, -decimals),
            },
        })

        chartRef.current = chart
        bidSeriesRef.current = bidSeries
        askSeriesRef.current = askSeries

        return () => {
            chart.remove()
        }
    }, [decimals])

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

    return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
