import os
import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import desc

#Imports internos
from .sql_models import Base, TickSQL


DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_db"
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