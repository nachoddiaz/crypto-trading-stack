import os
import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import desc

#Imports internos
from .sql_models import Base, TickSQL, CandleSQL
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
                        closed=c.closed
                    ) for c in candles
                ]
                session.add_all(sql_objects)
            # El commit es automático al salir del contexto
            print(f"💾 Persistidas {len(sql_objects)} velas para {symbol}.")

    async def get_recent_candles(self, symbol: str, limit: int = 1000):
        """Recupera velas históricas para el gráfico"""
        query = """
            SELECT time, open, high, low, close, volume 
            FROM candles 
            WHERE symbol = $1 
            ORDER BY time DESC 
            LIMIT $2
        """
        rows = await self.db_pool.fetch(query, symbol, limit)
        # Invertimos para que el frontend reciba cronológico (viejo -> nuevo)
        return list(reversed(rows))

    async def get_trades(self, limit: int = 100):
        """Recupera el historial de trades ejecutados"""
        # Asumiendo que tienes una tabla 'trades'. Si no, créala o usa redis.
        # Si guardas trades en JSON en una columna, adáptalo.
        query = "SELECT * FROM trades ORDER BY time DESC LIMIT $1"
        return await self.db_pool.fetch(query, limit)