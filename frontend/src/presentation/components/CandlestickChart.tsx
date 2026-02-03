// TradingView Lightweight Charts - Candlestick Component
import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts'
import { Candle } from '../../domain/types'

interface Props {
    candles: Candle[]
}

export default function CandlestickChart({ candles }: Props) {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

    useEffect(() => {
        if (!containerRef.current) return

        // Crear chart solo una vez
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
            height: 400,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        })

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#3fb950',
            downColor: '#f85149',
            borderUpColor: '#3fb950',
            borderDownColor: '#f85149',
            wickUpColor: '#3fb950',
            wickDownColor: '#f85149',
        })

        chartRef.current = chart
        seriesRef.current = candlestickSeries

        // Cleanup
        return () => {
            chart.remove()
        }
    }, [])

    // Actualizar datos cuando cambian las velas
    useEffect(() => {
        if (!seriesRef.current || candles.length === 0) return

        // Convertir timestamps a formato TradingView
        // Ordenar por tiempo y eliminar duplicados (lightweight-charts requiere tiempos únicos ascendentes)
        const seen = new Set<number>()
        const data: CandlestickData<Time>[] = candles
            .map(c => ({
                time: Math.floor(c.timestamp / 1000) as Time, // De ms a segundos
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
            }))
            .sort((a, b) => (a.time as number) - (b.time as number))
            .filter(c => {
                const t = c.time as number
                if (seen.has(t)) return false
                seen.add(t)
                return true
            })

        if (data.length > 0) {
            seriesRef.current.setData(data)
            chartRef.current?.timeScale().fitContent()
        }
    }, [candles])

    // Resize handler
    useEffect(() => {
        const handleResize = () => {
            if (containerRef.current && chartRef.current) {
                chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
            }
        }

        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    return <div ref={containerRef} style={{ width: '100%', height: '400px' }} />
}
