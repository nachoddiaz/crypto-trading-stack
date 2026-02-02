import os
import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import desc

#Imports internos
from .sql_models import Base, TickSQL, CandleSQL, TradeSQL
from src.core.models import Candle


DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres_db"
)

class AsyncRepository:
    def __init__(self):
        # echo=False para producción (True ensucia la consola con SQL)
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        
        # Fábrica de sesiones asíncronas
        self.async_session = sessionmaker(
            self.engine, 
            expire_on_commit=False, 
            class_=AsyncSession
        )

    async def init_db(self):
        """Crea las tablas en la base de datos si no existen."""
        async with self.engine.begin() as conn:
            # Elimina y recrea tablas (CUIDADO: Solo para desarrollo/reset)
            # await conn.run_sync(Base.metadata.drop_all) 
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Tablas de base de datos inicializadas.")

    async def save_batch(self, ticks_data: List[Dict[str, Any]]):
        """
        Recibe una lista de diccionarios (del buffer) y los inserta de golpe.
        Es mucho más eficiente que insertar uno a uno.
        """
        if not ticks_data:
            return

        async with self.async_session() as session:
            async with session.begin():
                # Convertimos diccionarios a objetos SQL
                sql_objects = [
                    TickSQL(
                        symbol=t['symbol'],
                        exchange_time=t['time'], # Ojo: mapeo time -> exchange_time
                        bid_price=t['bid_price'],
                        ask_price=t['ask_price'],
                        bid_quantity=t['bid_quantity'],
                        ask_quantity=t['ask_quantity'],
                        reservation_price=t.get('reservation_price'),
                        volatility=t.get('vol')
                    ) for t in ticks_data
                ]
                session.add_all(sql_objects)
            # El commit ocurre automáticamente al salir del bloque 'async with session.begin()'

    async def get_latest_ticks(self, symbol: str, limit: int = 5):
        """Método auxiliar para verificar datos (no usado en hot path)."""
        async with self.async_session() as session:
            stmt = select(TickSQL).filter_by(symbol=symbol).order_by(desc(TickSQL.exchange_time)).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def save_candles(self, symbol: str, candles: List[Candle]):

        """
        Guarda un lote de velas históricas de forma eficiente (Batch Insert).
        Argumentos:
            symbol: El par (ej. 'BTCUSDT'). Se pasa aparte para no repetirlo en cada objeto Candle en memoria.
            candles: Lista de objetos Candle (dataclass).
        """
        if not candles:
            return

        async with self.async_session() as session:
            async with session.begin():
                # Golden Rule: Operation Fusion. 
                # Creamos la lista de objetos ORM en una comprensión (rápida) y insertamos de golpe.
                sql_objects = [
                    CandleSQL(
                        symbol=symbol,
                        timestamp=c.timestamp,
                        open=c.open,
                        high=c.high,
                        low=c.low,
                        close=c.close,
                        volume=c.volume,
                        closed=c.closed,
                        volatility=c.volatility,
                        reservation_price_neutral=c.reservation_price_neutral
                    ) for c in candles
                ]
                session.add_all(sql_objects)
            # El commit es automático al salir del contexto
            print(f"💾 Persistidas {len(sql_objects)} velas para {symbol}.")

    async def get_recent_candles(self, symbol: str, limit: int = 1000):
        """Recupera velas para el gráfico y la estrategia."""
        async with self.async_session() as session:
            # Usamos ORM de SQLAlchemy en vez de SQL crudo
            stmt = (
                select(CandleSQL)
                .filter(CandleSQL.symbol == symbol)
                .order_by(desc(CandleSQL.timestamp))
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            # Devolvemos en orden cronológico (viejo -> nuevo)
            return list(reversed(rows))

    async def save_trade(self, trade_dict: Dict[str, Any]):
        """Guarda un trade individual ejecutado por el Engine."""
        async with self.async_session() as session:
            async with session.begin():
                trade_obj = TradeSQL(
                    symbol=trade_dict['symbol'],
                    timestamp=trade_dict['timestamp'],
                    side=trade_dict['side'],
                    price=trade_dict['price'],
                    qty=trade_dict['qty'],
                    total_usdt=trade_dict['total_usdt'],
                    edge_delta=trade_dict.get('edge_delta'),
                    q_optimal_theory=trade_dict.get('q_optimal_theory')
                )
                session.add(trade_obj)
            # Commit automático al salir
            print(f"💰 Trade guardado en DB: {trade_dict['side']} {trade_dict['symbol']}")

    async def get_trades(self, limit: int = 100):
        """Recupera el historial de trades para la API."""
        async with self.async_session() as session:
            # Usamos la sintaxis moderna de SQLAlchemy 1.4+ / 2.0
            stmt = (
                select(TradeSQL)
                .order_by(desc(TradeSQL.timestamp))
                .limit(limit)
            )
            result = await session.execute(stmt)
            trades = result.scalars().all()
            
            # Convertimos a diccionario para que Pydantic (API) lo lea fácil
            return [
                {
                    "timestamp": t.timestamp,
                    "symbol": t.symbol,
                    "side": t.side,
                    "price": t.price,
                    "qty": t.qty,
                    "total_usdt": t.total_usdt,
                    "edge_delta": t.edge_delta,
                    "q_optimal_theory": t.q_optimal_theory
                }
                for t in trades
            ]