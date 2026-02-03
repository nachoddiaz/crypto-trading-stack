import { useState, useEffect, useCallback } from 'react'
import CandlestickChart from './presentation/components/CandlestickChart'
import BidAskChart from './presentation/components/BidAskChart'
import PnLCards from './presentation/components/PnLCards'
import TradeTable from './presentation/components/TradeTable'
import { fetchSymbols, fetchCandles, fetchPnL, fetchTrades } from './infrastructure/api/tradingApi'
import { useWebSocket } from './infrastructure/hooks/useWebSocket'
import { Candle, Trade, PnLMetrics, BidAskTick } from './domain/types'

const WS_URL = `ws://${window.location.hostname}:8000/ws/live`

function App() {
    const [symbols, setSymbols] = useState<string[]>([])
    const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT')
    const [candles, setCandles] = useState<Candle[]>([])
    const [liveTicks, setLiveTicks] = useState<BidAskTick[]>([])
    const [trades, setTrades] = useState<Trade[]>([])
    const [pnl, setPnL] = useState<PnLMetrics | null>(null)
    const [wsConnected, setWsConnected] = useState(false)

    // Cargar símbolos disponibles
    useEffect(() => {
        fetchSymbols().then(setSymbols)
    }, [])

    // Cargar datos iniciales cuando cambia el símbolo
    useEffect(() => {
        fetchCandles(selectedSymbol).then(setCandles)
        fetchTrades().then(setTrades)
        fetchPnL().then(setPnL)
        // Limpiar ticks en vivo al cambiar símbolo
        setLiveTicks([])
    }, [selectedSymbol])

    // Auto-refresh de velas cada 60 segundos
    useEffect(() => {
        const interval = setInterval(() => {
            fetchCandles(selectedSymbol).then(setCandles)
        }, 60000) // 60 segundos

        return () => clearInterval(interval)
    }, [selectedSymbol])

    // Auto-refresh de trades cada 30 segundos
    useEffect(() => {
        const interval = setInterval(() => {
            fetchTrades().then(setTrades)
            fetchPnL().then(setPnL)
        }, 30000) // 30 segundos

        return () => clearInterval(interval)
    }, [])

    // Handler para mensajes WebSocket
    const handleWebSocketMessage = useCallback((data: any) => {
        if (data.type === 'TICK' && data.symbol === selectedSymbol) {
            const newTick: BidAskTick = {
                timestamp: data.timestamp,
                bid_price: data.bid_price,
                ask_price: data.ask_price
            }

            // Añadir tick y mantener máximo 500 puntos
            setLiveTicks(prev => {
                const updated = [...prev, newTick]
                return updated.slice(-500)
            })
        }

        // Si llega un trade, refrescar la tabla
        if (data.type === 'TRADE') {
            fetchTrades().then(setTrades)
        }
    }, [selectedSymbol])

    // Conectar WebSocket
    const { isConnected } = useWebSocket({
        url: WS_URL,
        onMessage: handleWebSocketMessage
    })

    useEffect(() => {
        setWsConnected(isConnected)
    }, [isConnected])

    return (
        <div className="dashboard">
            <header className="header">
                <h1>Hesperides Trading Dashboard</h1>
                <div className="header-controls">
                    <span className={`ws-status ${wsConnected ? 'connected' : 'disconnected'}`}>
                        {wsConnected ? '🟢 Live' : '🔴 Offline'}
                    </span>
                    <select
                        className="select-symbol"
                        value={selectedSymbol}
                        onChange={(e) => setSelectedSymbol(e.target.value)}
                    >
                        {symbols.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                </div>
            </header>

            <section className="charts-row">
                <div className="chart-panel">
                    <div className="panel-title">Bid/Ask Real-Time</div>
                    <BidAskChart ticks={liveTicks} />
                </div>
                <div className="chart-panel">
                    <div className="panel-title">Candlestick (1m)</div>
                    <CandlestickChart candles={candles} trades={trades} />
                </div>
            </section>

            <section className="trades-section">
                <TradeTable trades={trades} />
            </section>

            <section className="metrics-section">
                {pnl && <PnLCards pnl={pnl} />}
            </section>
        </div>
    )
}

export default App
