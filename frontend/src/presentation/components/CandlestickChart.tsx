// TradingView Lightweight Charts - Candlestick Component with Trade Markers
import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time, SeriesMarker } from 'lightweight-charts'
import { Candle, Trade } from '../../domain/types'

interface Props {
    candles: Candle[]
    trades?: Trade[]
}

export default function CandlestickChart({ candles, trades = [] }: Props) {
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
        const seen = new Set<number>()
        const data: CandlestickData<Time>[] = candles
            .map(c => ({
                time: Math.floor(c.timestamp / 1000) as Time,
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

    // Actualizar marcadores cuando cambian los trades
    useEffect(() => {
        if (!seriesRef.current || trades.length === 0) return

        // Crear marcadores de compra/venta
        const markers: SeriesMarker<Time>[] = trades.map(trade => ({
            time: Math.floor(trade.timestamp / 1000) as Time,
            position: trade.side === 'BUY' ? 'belowBar' : 'aboveBar',
            color: trade.side === 'BUY' ? '#3fb950' : '#f85149',
            shape: trade.side === 'BUY' ? 'arrowUp' : 'arrowDown',
            text: `${trade.side} ${trade.qty.toFixed(4)}`,
        }))

        // Ordenar marcadores por tiempo (requerido por lightweight-charts)
        markers.sort((a, b) => (a.time as number) - (b.time as number))

        seriesRef.current.setMarkers(markers)
    }, [trades])

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
