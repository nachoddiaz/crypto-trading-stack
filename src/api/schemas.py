from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Esquema para Velas (Gráfico) ---
class CandleResponse(BaseModel):
    timestamp: float  # Unix timestamp (ms) para JS
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        from_attributes = True

# --- Esquema para Trades (Tabla de operaciones) ---
class TradeResponse(BaseModel):
    timestamp: float
    symbol: str
    side: str        # "BUY" o "SELL"
    price: float
    qty: float
    total_usdt: float
    edge_delta: Optional[float] = None
    q_optimal_theory: Optional[float] = None

# --- Esquema para Métricas (PnL y Balance) ---
class BalanceResponse(BaseModel):
    total_equity: float
    usdt_available: float
    btc_position: float
    pnl_absolute: float
    pnl_percent: float