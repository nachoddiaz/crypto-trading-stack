import asyncio
import sys
import os

# Ajuste de path para que encuentre 'src' desde la carpeta 'apps'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.redis_bus import RedisBus
from src.adapters.socket.binance_socket import BinanceDriver
from src.adapters.rest.binance_rest import BinanceRest
from src.core.market_state import MarketState
from src.database.repository import AsyncRepository
from src.core.models import Candle
from typing import List



async def main():
    bus = RedisBus(stream_key="binance_ticks")
    exchange_name = "binance"
    target_symbols  = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT", "TRXUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT"] #"HYPEUSDT"]
    start_date = "2026-01-01"

    # 1. Inicialización de Estrategias y Estado
    market_states = {}
    rest_client = BinanceRest()
    repo = AsyncRepository()

    # Inicialización de la base de datos
    print("🛠️ Inicializando base de datos...")
    await repo.init_db()

    # El consumidor (persister) puede estar apagado y los datos se guardarán en Redis igual.
    print(f"--- Iniciando carga histórica para {len(target_symbols)} pares ---")
    
    for symbol in target_symbols:
        print(f"📥 Descargando histórico para {symbol}...")
        
        # 1. Descargar (REST)
        history: List[Candle] = rest_client.get_historical_candles(symbol, interval="1h", start_str=start_date)
        
        # 2. Persistir (SQL) - "Cold Path" (se hace una vez al inicio)
        if history:
            # Usamos el repositorio importado anteriormente
            await repo.save_candles(symbol, history)
        
        
        state = MarketState(window_size=1000)
        state.initialize_history(history)
        market_states[symbol] = state

    # 2. Ingesta Tiempo Real (Socket)
    print("--- Iniciando WebSocket en Tiempo Real ---")

    if exchange_name == "binance":
        #Asigno el driver y el simbolo
        driver = BinanceDriver(bus)
        await driver.backoff(target_symbols)
    else:
        raise ValueError("Exchange no soportado")

    
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Ingestor detenido.")