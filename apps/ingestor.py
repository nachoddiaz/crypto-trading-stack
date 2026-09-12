import asyncio
import sys
import os
from typing import List, Dict


# Ajuste de path para que encuentre 'src' desde la carpeta 'apps'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.redis_bus import RedisBus
from src.adapters.socket.binance_socket import BinanceDriver
from src.adapters.rest.binance_rest import BinanceRest
from src.database.repository import AsyncRepository

from src.core.market_state import MarketState
from src.core.models import Candle, Registro
from src.core.trader_engine import TraderEngine
from src.core.strategies.portfolio_manager import PortfolioManager
from src.core.realtime_processor import RealTimeProcessor



async def setup_symbol(symbol: str, repo: AsyncRepository, rest_client: BinanceRest, start_date: str, redis_bus=None) -> tuple[str, RealTimeProcessor]:
    """
    Función auxiliar que configura TODO el stack para UNA sola moneda.
    Se ejecutará en paralelo para todas las monedas.
    """
    print(f"⚡ Iniciando setup para {symbol}...")

    # 1. Instanciar componentes lógicos
    market_state = MarketState(window_size=1000)
    engine = TraderEngine(initial_usdt=10000.0)
    pm = PortfolioManager([symbol]) # Cerebro específico para este símbolo

    # 2. Descarga Histórica (Cold Path)
    try:
        print(f"📥 Descargando histórico {symbol}...")
        history: List[Candle] = rest_client.get_historical_candles(symbol, interval="1s", start_str=start_date)
        
        if history:
            market_state.initialize_history(history)
            
            # Persistimos en SQL (BBDD)
            await repo.save_candles(symbol, history)
            print(f"✅ {symbol}: Cargadas {len(history)} velas.")
    except Exception as e:
        print(f"⚠️ Error cargando histórico para {symbol}: {e}")

    # 3. Crear el Orquestador (Processor)
    processor = RealTimeProcessor(
        symbol=symbol,
        market_state=market_state,
        engine=engine,
        portfolio_manager=pm,
        repository=repo,
        redis_bus=redis_bus  # Para publicar trades en tiempo real
    )
    
    # Asegurar que acepte datos nuevos inmediatos
    processor.last_second_processed = -1 

    return symbol, processor

async def main():
    bus = RedisBus(stream_key="binance_ticks")
    exchange_name = "binance"
    target_symbols  = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT", "TRXUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT"] #"HYPEUSDT"]
    start_date = "2026-02-06 14:40"

    # 1. Inicialización de Estrategias y Estado
    rest_client = BinanceRest()
    repo = AsyncRepository()

    # Inicialización de la base de datos
    print("🛠️ Inicializando base de datos...")
    await repo.init_db()

    print(f"🚀 Lanzando carga paralela para {len(target_symbols)} pares...")
    
    tasks = [setup_symbol(sym, repo, rest_client, start_date, bus) for sym in target_symbols]

    # Ejecutamos todas a la vez y esperamos los resultados
    results = await asyncio.gather(*tasks)

    processors: Dict[str, RealTimeProcessor] = dict(results)
    
    print("✅ Todos los procesadores listos en memoria.")

    print("--- Iniciando WebSocket en Tiempo Real ---")

    if exchange_name == "binance":
        #Asigno el driver y el simbolo
        queue = asyncio.Queue() # Cola en memoria de alta velocidad
        driver = BinanceDriver(bus) # Le pasamos el bus si lo necesita, pero inyectamos la queue
        driver.queue = queue
        # NOTE: subscribe() ya tiene @retry decorator, no hace falta backoff()
    else:
        raise ValueError("Exchange no soportado")

    
    
    async def consume():
        print("🎧 Escuchando WebSocket...")
        while True:
            # Esto es bloqueante (espera dato), eficiente para CPU
            tick_dict = await queue.get()
            
            # Validación rápida
            sym = tick_dict.get('symbol')
            
            # --- PUBLICAR A PUB/SUB PARA WEBSOCKETS ---
            # Esto permite broadcasting en tiempo real a todos los clientes conectados
            asyncio.create_task(bus.publish({
                "type": "TICK",
                "symbol": sym,
                "bid_price": tick_dict.get('bid_price'),
                "ask_price": tick_dict.get('ask_price'),
                "timestamp": tick_dict.get('time')
            }))
            
            # --- ROUTING SIN BUCLES ---
            # O(1) Lookup: Buscamos el procesador directamente por la clave
            if sym in processors:
                # Convertimos a objeto y despachamos
                tick = Registro(**tick_dict)
                # create_task para no bloquear el consumo del siguiente tick
                asyncio.create_task(processors[sym].on_tick(tick))
            
            queue.task_done()

    # 5. Ejecución Final
    print("--- Sistema HFT Iniciado ---")
    await asyncio.gather(
        driver.subscribe(target_symbols), # Inicia la conexión al Socket
        consume()                         # Inicia el router de mensajes
    )
    

    
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Ingestor detenido.")