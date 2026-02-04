import asyncio
import time
import websockets
from abc import ABC, abstractmethod  # Abstract Base Class
from typing import Optional
from src.core.models import Registro

class ExchangeDrivers(ABC):

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        #variables backoff
        self.initial_backoff = 1
        self.max_backoff = 60
        self.backoff_factor = 2

    async def backoff(self, symbols: list[str]):
        current_delay = self.initial_backoff
        while True:
            try:
                start_time = time.time()
                print(f"🔄 Intentando conectar a {symbols}...")
                await self.subscribe(symbols)

            except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                print(f"⚠️ Conexión perdida ({e}).")
            
            except Exception as e:
                print(f"❌ Error crítico inesperado: {e}")
            
            connection_duration = time.time() - start_time
            if connection_duration > 60:
                current_delay = self.initial_backoff

            print(f"⏳ Reintentando en {current_delay} segundos...")
            await asyncio.sleep(current_delay)
            current_delay = min(current_delay * self.backoff_factor, self.max_backoff)
        

    @abstractmethod
    async def subscribe(self, symbols: list[str]):
        """Método para conectarse al socket"""
        pass

    @abstractmethod
    async def normlize_message(self, raw_msg: str) -> Optional[Registro]:
        """Método obligatorio para traducir el JSON del exchange al formato común"""
        pass
