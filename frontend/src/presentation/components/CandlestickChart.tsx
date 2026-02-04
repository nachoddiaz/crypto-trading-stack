// TradingView Lightweight Charts - Candlestick Component with Trade Markers and Moving Averages
import { useEffect, useRef, useMemo } from 'react'
import { createChart, IChartApi, ISeriesApi, Time, SeriesMarker, LineData } from 'lightweight-charts'
import { Candle, Trade } from '../../domain/types'

interface MAParams {
    fast: number
    slow: number
}

interface Props {
    candles: Candle[]
    trades?: Trade[]
    maParams?: MAParams | null
}

// Calcular media móvil simple
function calculateSMA(data: number[], period: number): (number | null)[] {
    const result: (number | null)[] = []
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            result.push(null)
        } else {
            let sum = 0
            for (let j = 0; j < period; j++) {
                sum += data[i - j]
            }
            result.push(sum / period)
        }
    }
    return result
}

export default function CandlestickChart({ candles, trades = [], maParams }: Props) {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
    const fastMARef = useRef<ISeriesApi<'Line'> | null>(null)
    const slowMARef = useRef<ISeriesApi<'Line'> | null>(null)

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
                secondsVisible: true,
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

        // Añadir líneas para MAs
        const fastMA = chart.addLineSeries({
            color: '#58a6ff',
            lineWidth: 2,
            title: 'MA Rápida',
        })

        const slowMA = chart.addLineSeries({
            color: '#f0883e',
            lineWidth: 2,
            title: 'MA Lenta',
        })

        chartRef.current = chart
        seriesRef.current = candlestickSeries
        fastMARef.current = fastMA
        slowMARef.current = slowMA

        // Cleanup
        return () => {
            chart.remove()
        }
    }, [])

    // Preparar datos ordenados y únicos
    const chartData = useMemo(() => {
        if (candles.length === 0) return { candleData: [], closes: [], times: [] }

        const seen = new Set<number>()
        const sorted = candles
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

        return {
            candleData: sorted,
            closes: sorted.map(c => c.close),
            times: sorted.map(c => c.time),
        }
    }, [candles])

    // Actualizar velas
    useEffect(() => {
        if (!seriesRef.current || chartData.candleData.length === 0) return
        seriesRef.current.setData(chartData.candleData)
        chartRef.current?.timeScale().fitContent()
    }, [chartData])

    // Actualizar MAs
    useEffect(() => {
        if (!fastMARef.current || !slowMARef.current) return

        if (!maParams || chartData.closes.length === 0) {
            // Limpiar MAs si no hay parámetros
            fastMARef.current.setData([])
            slowMARef.current.setData([])
            return
        }

        const { fast, slow } = maParams
        const fastValues = calculateSMA(chartData.closes, fast)
        const slowValues = calculateSMA(chartData.closes, slow)

        const fastData: LineData<Time>[] = []
        const slowData: LineData<Time>[] = []

        for (let i = 0; i < chartData.times.length; i++) {
            if (fastValues[i] !== null) {
                fastData.push({ time: chartData.times[i], value: fastValues[i]! })
            }
            if (slowValues[i] !== null) {
                slowData.push({ time: chartData.times[i], value: slowValues[i]! })
            }
        }

        fastMARef.current.setData(fastData)
        slowMARef.current.setData(slowData)
    }, [chartData, maParams])

    // Actualizar marcadores cuando cambian los trades
    useEffect(() => {
        if (!seriesRef.current) return

        if (trades.length === 0) {
            seriesRef.current.setMarkers([])
            return
        }

        console.log('CandlestickChart: Processing trades', trades)

        const markers: SeriesMarker<Time>[] = trades.map(trade => ({
            time: Math.floor(trade.timestamp) as Time,
            position: trade.side === 'BUY' ? 'belowBar' : 'aboveBar',
            color: trade.side === 'BUY' ? '#3fb950' : '#f85149',
            shape: trade.side === 'BUY' ? 'arrowUp' : 'arrowDown',
            text: `${trade.side} ${trade.qty.toFixed(4)}`,
        }))

        // Debug: Check if markers match available candle times
        const availableTimes = new Set(chartData.times as number[])
        const validMarkers = markers.filter(m => availableTimes.has(m.time as number))

        console.log(`CandlestickChart: Values`, {
            totalTrades: trades.length,
            totalMarkers: markers.length,
            validMarkersMatchingCandles: validMarkers.length,
            sampleMarker: markers[0],
            sampleCandleTime: chartData.times[chartData.times.length - 1]
        })

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

    return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
