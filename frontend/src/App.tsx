import { useState, useEffect } from 'react'
import CandlestickChart from './presentation/components/CandlestickChart'
import BidAskChart from './presentation/components/BidAskChart'
import PnLCards from './presentation/components/PnLCards'
import TradeTable from './presentation/components/TradeTable'
import { fetchSymbols, fetchCandles, fetchPnL, fetchTrades, fetchTicks } from './infrastructure/api/tradingApi'
import { Candle, Trade, PnLMetrics, BidAskTick } from './domain/types'

function App() {
    const [symbols, setSymbols] = useState<string[]>([])
    const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT')
    const [candles, setCandles] = useState<Candle[]>([])
    const [ticks, setTicks] = useState<BidAskTick[]>([])
    const [trades, setTrades] = useState<Trade[]>([])
    const [pnl, setPnL] = useState<PnLMetrics | null>(null)

    // Cargar símbolos disponibles
    useEffect(() => {
        fetchSymbols().then(setSymbols)
    }, [])

    // Cargar datos cuando cambia el símbolo
    useEffect(() => {
        fetchCandles(selectedSymbol).then(setCandles)
        fetchTicks(selectedSymbol).then(setTicks)
        fetchTrades().then(setTrades)
        fetchPnL().then(setPnL)
    }, [selectedSymbol])

    return (
        <div className="dashboard">
            <header className="header">
                <h1>Hesperides Trading Dashboard</h1>
                <select
                    className="select-symbol"
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value)}
                >
                    {symbols.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
            </header>

            <section className="charts-row">
                <div className="chart-panel">
                    <div className="panel-title">Bid/Ask Evolution</div>
                    <BidAskChart ticks={ticks} />
                </div>
                <div className="chart-panel">
                    <div className="panel-title">Candlestick (1m)</div>
                    <CandlestickChart candles={candles} />
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
