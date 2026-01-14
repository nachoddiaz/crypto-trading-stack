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
    
    return [
        {
            "timestamp": r["time"],
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["volume"]
        }
        for r in rows
    ]

@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(repo: AsyncRepository = Depends(get_repo)):
    """Devuelve la tabla de trades"""
    # Si aún no tienes tabla SQL de trades, devuelve lista vacía o mock
    # rows = await repo.get_trades()
    return [] 

@router.get("/metrics", response_model=BalanceResponse)
async def get_metrics():
    """
    Devuelve el estado actual de la cuenta.
    NOTA: En producción, esto debería leerse de Redis donde el TraderEngine
    escribe su estado actual cada segundo.
    """
    # MOCK DATA (Hasta que conectemos Redis)
    return {
        "total_equity": 10500.50,
        "usdt_available": 500.50,
        "btc_position": 0.2,
        "pnl_absolute": 500.50,
        "pnl_percent": 5.0
    }