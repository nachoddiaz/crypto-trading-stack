// Infrastructure Layer - API Adapter
import { Candle, Trade, PnLMetrics, BidAskTick, Position } from '../../domain/types'

const API_BASE = '/api'

export async function fetchSymbols(): Promise<string[]> {
    try {
        const res = await fetch(`${API_BASE}/symbols`)
        const data = await res.json()
        return data.symbols || []
    } catch (error) {
        console.error('Error fetching symbols:', error)
        return ['BTCUSDT', 'ETHUSDT'] // Fallback
    }
}

export async function fetchCandles(symbol: string, limit = 500): Promise<Candle[]> {
    try {
        const res = await fetch(`${API_BASE}/candles/${symbol}?limit=${limit}`)
        return await res.json()
    } catch (error) {
        console.error('Error fetching candles:', error)
        return []
    }
}

export async function fetchTrades(limit = 100): Promise<Trade[]> {
    try {
        const res = await fetch(`${API_BASE}/trades?limit=${limit}`)
        return await res.json()
    } catch (error) {
        console.error('Error fetching trades:', error)
        return []
    }
}

export async function fetchPnL(): Promise<PnLMetrics> {
    try {
        const res = await fetch(`${API_BASE}/pnl`)
        return await res.json()
    } catch (error) {
        console.error('Error fetching PnL:', error)
        return { daily: 0, monthly: 0, qtd: 0, ytd: 0, total: 0 }
    }
}

export async function fetchMetrics() {
    try {
        const res = await fetch(`${API_BASE}/metrics`)
        return await res.json()
    } catch (error) {
        console.error('Error fetching metrics:', error)
        return null
    }
}

export async function fetchTicks(symbol: string, limit = 500): Promise<BidAskTick[]> {
    try {
        const res = await fetch(`${API_BASE}/ticks/${symbol}?limit=${limit}`)
        return await res.json()
    } catch (error) {
        console.error('Error fetching ticks:', error)
        return []
    }
}

export async function fetchPositions(): Promise<Position[]> {
    try {
        const res = await fetch(`${API_BASE}/positions`)
        const data = await res.json()
        return data.positions || []
    } catch (error) {
        console.error('Error fetching positions:', error)
        return []
    }
}

export async function fetchStrategies(): Promise<string[]> {
    try {
        const res = await fetch(`${API_BASE}/strategies`)
        const data = await res.json()
        return data.strategies || []
    } catch (error) {
        console.error('Error fetching strategies:', error)
        return ['SMA', 'MOMENTUM', 'ENGULFING'] // Fallback
    }
}
