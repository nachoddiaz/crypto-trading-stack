// Domain Types - Entidades puras del negocio

export interface Candle {
    timestamp: number
    open: number
    high: number
    low: number
    close: number
    volume: number
}

export interface Trade {
    timestamp: number
    symbol: string
    side: 'BUY' | 'SELL'
    price: number
    qty: number
    total_usdt: number
    edge_delta?: number
    q_optimal_theory?: number
}

export interface PnLMetrics {
    daily: number
    monthly: number
    qtd: number
    ytd: number
    total: number
    equity?: number
    initial_capital?: number
    total_trades?: number
}

export interface Position {
    symbol: string
    qty?: number
    quantity?: number
    last_trade?: Trade
    avg_price?: number
    current_price?: number
    pnl_unrealized?: number
}

export interface BalanceMetrics {
    total_equity: number
    usdt_available: number
    btc_position: number
    pnl_absolute: number
    pnl_percent: number
}

export interface BidAskTick {
    timestamp: number
    bid_price: number
    ask_price: number
}
