from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.database.repository import AsyncRepository
from src.api.schemas import CandleResponse, TradeResponse, BalanceResponse

router = APIRouter()

# Inyección de dependencia para la DB
async def get_repo():
    repo = AsyncRepository()
    await repo.init_db() # Asegura conexión
    return repo

@router.get("/candles/{symbol}", response_model=List[CandleResponse])
async def get_candles(symbol: str, limit: int = 500, repo: AsyncRepository = Depends(get_repo)):
    """Devuelve histórico OHLCV para pintar el gráfico"""
    rows = await repo.get_recent_candles(symbol, limit)
    
    # rows son objetos CandleSQL (ORM), accedemos a atributos, no dict keys
    return [
        {
            "timestamp": r.timestamp,  # Era r["time"], corregido a r.timestamp
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume
        }
        for r in rows
    ]

@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(limit: int = 100, repo: AsyncRepository = Depends(get_repo)):
    """Devuelve la tabla de trades ejecutados"""
    trades = await repo.get_trades(limit)
    return trades  # Ya viene formateado como lista de dicts desde el repo 

@router.get("/metrics", response_model=BalanceResponse)
async def get_metrics():
    """
    Devuelve el estado actual de la cuenta.
    TODO: Leer de Redis donde el TraderEngine escribe su estado.
    """
    # MOCK DATA (Hasta que conectemos Redis)
    return {
        "total_equity": 10500.50,
        "usdt_available": 500.50,
        "btc_position": 0.2,
        "pnl_absolute": 500.50,
        "pnl_percent": 5.0
    }

# --- NUEVOS ENDPOINTS ---

@router.get("/symbols")
async def get_symbols():
    """Lista de símbolos disponibles para el dropdown del frontend"""
    return {
        "symbols": [
            "BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT",
            "TRXUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT"
        ]
    }

@router.get("/pnl")
async def get_pnl():
    """
    PnL desglosado: daily, monthly, QTD, YTD, total.
    TODO: Conectar a PortfolioManager.calculate_pnl_metrics()
    """
    return {
        "daily": 0.0,
        "monthly": 0.0,
        "qtd": 0.0,
        "ytd": 0.0,
        "total": 0.0
    }

@router.get("/positions")
async def get_positions():
    """
    Posiciones abiertas actuales.
    TODO: Conectar a TraderEngine.get_positions()
    """
    return {
        "positions": []
    }

@router.get("/ticks/{symbol}")
async def get_ticks(symbol: str, limit: int = 500, repo: AsyncRepository = Depends(get_repo)):
    """Devuelve histórico de bid/ask para el gráfico de spread"""
    rows = await repo.get_recent_ticks(symbol, limit)
    return [
        {
            "timestamp": r.exchange_time,
            "bid_price": r.bid_price,
            "ask_price": r.ask_price
        }
        for r in rows
    ]