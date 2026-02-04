from fastapi import APIRouter, Depends
from typing import List
from src.database.repository import AsyncRepository
from src.api.schemas import CandleResponse, TradeResponse, BalanceResponse
from src.infrastructure.redis_bus import RedisBus

router = APIRouter()

# Inyección de dependencias
async def get_repo():
    repo = AsyncRepository()
    await repo.init_db()
    return repo

async def get_redis():
    bus = RedisBus(stream_key="binance_ticks")
    return bus

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
async def get_pnl(redis: RedisBus = Depends(get_redis), repo: AsyncRepository = Depends(get_repo)):
    """
    PnL Mark-to-Market: Valoración de posiciones a precios actuales.
    PnL% = ((USDT_balance + Σ(position_qty × current_price)) / initial_capital) - 1
    """
    
    # Capital inicial por engine (debe coincidir con TraderEngine en ingestor.py)
    CAPITAL_PER_ENGINE = 10000.0
    
    # 1. Obtener estados de todos los engines desde Redis
    states = await redis.get_all_engine_states()
    
    if not states:
        return {
            "daily": 0.0, "monthly": 0.0, "qtd": 0.0, "ytd": 0.0, "total": 0.0,
            "total_trades": 0, "equity": CAPITAL_PER_ENGINE, "initial_capital": CAPITAL_PER_ENGINE
        }
    
    # Capital inicial total = número de engines × capital por engine
    num_engines = len(states)
    initial_capital = num_engines * CAPITAL_PER_ENGINE
    
    # 2. Agregar balances de todos los engines
    total_usdt = 0.0
    all_crypto = {}  # symbol -> qty
    total_trades = 0
    
    for symbol, state in states.items():
        total_usdt += state.get("usdt_balance", 0.0)
        crypto_balances = state.get("crypto_balances", {})
        total_trades += state.get("total_trades", 0)
        
        for asset, qty in crypto_balances.items():
            if qty != 0:
                all_crypto[asset] = all_crypto.get(asset, 0.0) + qty
    
    # 3. Obtener precios actuales desde las últimas velas en BD
    crypto_value = 0.0
    for asset, qty in all_crypto.items():
        # Buscar última vela del activo para obtener precio
        candles = await repo.get_recent_candles(asset, limit=1)
        if candles:
            current_price = candles[0].close
            crypto_value += qty * current_price
    
    # 4. Calcular equity total y PnL  
    total_equity = total_usdt + crypto_value
    total_pnl_pct = ((total_equity / initial_capital) - 1) * 100 if initial_capital > 0 else 0.0
    
    # Para daily/monthly/qtd/ytd necesitamos snapshots históricos
    # Por simplicidad, usamos el PnL total para todos los períodos 
    # ya que no tenemos snapshots de equity en cada período
    # TODO: Implementar equity_snapshots table para tracking histórico
    
    return {
        "daily": round(total_pnl_pct, 2),
        "monthly": round(total_pnl_pct, 2),
        "qtd": round(total_pnl_pct, 2),
        "ytd": round(total_pnl_pct, 2),
        "total": round(total_pnl_pct, 2),
        "total_trades": total_trades,
        "equity": round(total_equity, 2),
        "initial_capital": initial_capital
    }

@router.get("/positions")
async def get_positions(redis: RedisBus = Depends(get_redis)):
    """
    Posiciones abiertas actuales.
    Lee estado de todos los TraderEngines desde Redis.
    """
    states = await redis.get_all_engine_states()
    
    positions = []
    for symbol, state in states.items():
        crypto_balances = state.get("crypto_balances", {})
        for asset, qty in crypto_balances.items():
            if qty != 0:  # Solo mostrar posiciones no-cero
                positions.append({
                    "symbol": asset,
                    "quantity": qty,
                    "last_trade": state.get("last_trade")
                })
    
    return {
        "positions": positions
    }

@router.get("/strategies")
async def get_strategies():
    """Lista de estrategias disponibles para filtrado."""
    return {
        "strategies": ["SMA", "MOMENTUM", "ENGULFING"]
    }

@router.get("/strategy-params")
async def get_strategy_params(strategy: str = "ALL"):
    """Devuelve los parámetros de estrategia por símbolo."""
    import json
    import os
    
    # Cargar el archivo de parámetros
    params_path = os.path.join(os.path.dirname(__file__), "../config/strategy_params.json")
    try:
        with open(params_path, 'r') as f:
            all_params = json.load(f)
    except FileNotFoundError:
        return {"error": "Config file not found", "params": {}}
    
    # Mapeo de nombres de estrategia
    strategy_key_map = {
        "SMA": "MA_CROSS",
        "MOMENTUM": "MOMENTUM",
        "ENGULFING": "CANDLE_ENGULF"
    }
    
    # Si piden una estrategia específica, filtrar
    if strategy != "ALL" and strategy in strategy_key_map:
        key = strategy_key_map[strategy]
        result = {}
        for symbol, strats in all_params.items():
            if key in strats:
                result[symbol] = strats[key]
        return {"strategy": strategy, "params": result}
    
    # Devolver todo
    return {"strategy": "ALL", "params": all_params}

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