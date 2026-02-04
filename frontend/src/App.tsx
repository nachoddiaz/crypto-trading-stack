import { useState, useEffect, useCallback, useMemo } from 'react'
import CandlestickChart from './presentation/components/CandlestickChart'
import BidAskChart from './presentation/components/BidAskChart'
import PnLCards from './presentation/components/PnLCards'
import TradeTable from './presentation/components/TradeTable'
import PositionsTable from './presentation/components/PositionsTable'
import FilterPanel from './presentation/components/FilterPanel'
import StrategyParamsPanel from './presentation/components/StrategyParamsPanel'
import { fetchSymbols, fetchCandles, fetchPnL, fetchTrades, fetchPositions, fetchStrategies } from './infrastructure/api/tradingApi'
import { useWebSocket } from './infrastructure/hooks/useWebSocket'
import { Candle, Trade, PnLMetrics, BidAskTick, Position } from './domain/types'

const WS_URL = `ws://${window.location.hostname}:8000/ws/live`

// Helper para formatear fecha como YYYY-MM-DD
function formatDate(date: Date): string {
    return date.toISOString().split('T')[0]
}

function App() {
    const [symbols, setSymbols] = useState<string[]>([])
    const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT')
    const [candles, setCandles] = useState<Candle[]>([])
    const [liveTicks, setLiveTicks] = useState<BidAskTick[]>([])
    const [trades, setTrades] = useState<Trade[]>([])
    const [positions, setPositions] = useState<Position[]>([])
    const [pnl, setPnL] = useState<PnLMetrics | null>(null)
    const [wsConnected, setWsConnected] = useState(false)

    // Filters state
    const [strategies, setStrategies] = useState<string[]>([])
    const [selectedStrategy, setSelectedStrategy] = useState('ALL')
    const [startDate, setStartDate] = useState(() => {
        const d = new Date()
        d.setMonth(d.getMonth() - 1) // Default: último mes
        return formatDate(d)
    })
    const [endDate, setEndDate] = useState(() => formatDate(new Date()))

    // MA params para graficar en CandlestickChart
    const [maParams, setMAParams] = useState<{ fast: number, slow: number } | null>(null)

    // Cargar parámetros de MA cuando cambia la estrategia o símbolo
    useEffect(() => {
        if (selectedStrategy === 'SMA') {
            fetch(`/api/strategy-params?strategy=SMA`)
                .then(res => res.json())
                .then(data => {
                    const params = data.params?.[selectedSymbol]
                    if (params) {
                        setMAParams({ fast: params.fast, slow: params.slow })
                    } else {
                        setMAParams(null)
                    }
                })
                .catch(() => setMAParams(null))
        } else {
            setMAParams(null)
        }
    }, [selectedStrategy, selectedSymbol])

    // Cargar símbolos y estrategias disponibles
    useEffect(() => {
        fetchSymbols().then(setSymbols)
        fetchStrategies().then(setStrategies)
    }, [])

    // Cargar datos iniciales cuando cambia el símbolo
    useEffect(() => {
        fetchCandles(selectedSymbol).then(setCandles)
        fetchTrades().then(setTrades)
        fetchPositions().then(setPositions)
        fetchPnL().then(setPnL)
        setLiveTicks([])
    }, [selectedSymbol])

    // Auto-refresh de velas cada 1 segundo
    useEffect(() => {
        const interval = setInterval(() => {
            fetchCandles(selectedSymbol).then(setCandles)
        }, 1000)
        return () => clearInterval(interval)
    }, [selectedSymbol])

    // Auto-refresh de trades y posiciones cada 30 segundos
    useEffect(() => {
        const interval = setInterval(() => {
            fetchTrades().then(setTrades)
            fetchPositions().then(setPositions)
            fetchPnL().then(setPnL)
        }, 30000)
        return () => clearInterval(interval)
    }, [])

    // Filtrar trades por símbolo, estrategia y fecha
    const filteredTrades = useMemo(() => {
        return trades.filter(trade => {
            // Filtro por símbolo seleccionado (para que las flechas solo se muestren en el gráfico correcto)
            if (trade.symbol !== selectedSymbol) {
                return false
            }

            // Filtro por estrategia (si el trade tiene campo strategy)
            if (selectedStrategy !== 'ALL') {
                // Asumimos que el trade puede tener strategy_id o lo inferimos
                const tradeStrategy = (trade as any).strategy_id
                if (tradeStrategy && tradeStrategy !== selectedStrategy) {
                    return false
                }
            }

            // Filtro por fecha
            const tradeDate = new Date(trade.timestamp * 1000)
            const start = new Date(startDate)
            const end = new Date(endDate)
            end.setHours(23, 59, 59, 999) // Incluir todo el día final

            return tradeDate >= start && tradeDate <= end
        })
    }, [trades, selectedSymbol, selectedStrategy, startDate, endDate])

    // Handler para mensajes WebSocket
    const handleWebSocketMessage = useCallback((data: any) => {
        if (data.type === 'TICK' && data.symbol === selectedSymbol) {
            const newTick: BidAskTick = {
                timestamp: data.timestamp,
                bid_price: data.bid_price,
                ask_price: data.ask_price
            }
            setLiveTicks(prev => {
                const updated = [...prev, newTick]
                return updated.slice(-500)
            })
        }
        if (data.type === 'TRADE') {
            // Refrescar trades, posiciones y PnL cuando llega un trade nuevo
            // Añadimos .catch para evitar crashes por errores de red
            fetchTrades().then(setTrades).catch(err => console.error('Error fetching trades:', err))
            fetchPositions().then(setPositions).catch(err => console.error('Error fetching positions:', err))
            fetchPnL().then(setPnL).catch(err => console.error('Error fetching PnL:', err))
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

            {/* Filtros de estrategia y fecha */}
            <section className="filters-section">
                <FilterPanel
                    strategies={strategies}
                    selectedStrategy={selectedStrategy}
                    onStrategyChange={setSelectedStrategy}
                    startDate={startDate}
                    endDate={endDate}
                    onStartDateChange={setStartDate}
                    onEndDateChange={setEndDate}
                />
            </section>

            {/* Parámetros de la estrategia seleccionada */}
            {selectedStrategy !== 'ALL' && (
                <section className="strategy-params-section">
                    <div className="panel-title">Parámetros {selectedStrategy} - {selectedSymbol}</div>
                    <StrategyParamsPanel strategy={selectedStrategy} symbol={selectedSymbol} />
                </section>
            )}

            <section className="charts-row">
                <div className="chart-panel">
                    <div className="panel-title">Bid/Ask Real-Time ({selectedSymbol})</div>
                    <BidAskChart ticks={liveTicks} />
                </div>
                <div className="chart-panel">
                    <div className="panel-title">
                        Candlestick {selectedStrategy === 'SMA' && maParams ? `(MA ${maParams.fast}/${maParams.slow})` : ''}
                    </div>
                    <CandlestickChart
                        candles={candles}
                        trades={filteredTrades}
                        maParams={selectedStrategy === 'SMA' ? maParams : null}
                    />
                </div>
            </section>

            <section className="tables-row">
                <div className="table-panel">
                    <div className="panel-title">Posiciones Abiertas ({positions.length})</div>
                    <div className="table-wrapper">
                        <PositionsTable positions={positions} />
                    </div>
                </div>
                <div className="table-panel">
                    <div className="panel-title">Trades ({filteredTrades.length})</div>
                    <div className="table-wrapper">
                        <TradeTable trades={filteredTrades} />
                    </div>
                </div>
            </section>

            <section className="metrics-section">
                {pnl && <PnLCards pnl={pnl} />}
            </section>
        </div>
    )
}

export default App
