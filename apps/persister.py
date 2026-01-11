import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.redis_bus import RedisBus
from src.database.repository import AsyncRepository
from src.core.data_persister import DataPersister
from src.core.models import Registro

from src.core.reserve_price import ReservePrice

async def main():
    # 1. Configurar Infraestructura (Redis)
    bus = RedisBus(
        stream_key="binance_ticks",
        group_name="db_writers",
        consumer_name="worker_1"
    )
    await bus.initialize()

    # 2. Configurar Lógica de Negocio y DB
    repo = AsyncRepository()
    persister = DataPersister(repository=repo)

    strategies: Dict[str, ReservePrice] = {}

    print("--- Persister Iniciado: Escuchando Redis ---")

    # 3. El Bucle Infinito (The Event Loop)
    while True:
        raw_batch = await bus.consume_batch(batch_size=50, block_ms=2000)
        
        if not raw_batch:
            continue

        processed_batch = []
        
        for msg in raw_batch:
            symbol = msg.get('symbol')
            
            # A. Inicializamos la "memoria" de esa moneda si es la primera vez que la vemos
            if symbol not in strategies:
                strategies[symbol] = ReservePrice(symbol)
            
            # B. Reconstruimos el objeto Registro (Tu función lo necesita)
            # Usamos un try/except ligero por si llega basura de Redis
            try:
                tick = Registro(**msg)
            except TypeError:
                continue

            # C. --- AQUÍ LLAMAS A TU FUNCIÓN ---
            # Al usar la instancia en 'strategies', la volatilidad se mantiene correcta
            resultado = strategies[symbol]._calc_reservation_price(tick)

            # D. Actualizamos el mensaje original con los datos calculados
            # Tu función retorna un dict con 'reservation_price' y 'vol', así que lo aprovechamos
            msg['reservation_price'] = resultado['reservation_price']
            msg['vol'] = resultado['vol']
            
            processed_batch.append(msg)

        # B. Procesar y Guardar (Hot Path)
        try:
            if processed_batch:
                await persister.save_batch(processed_batch)
        except Exception as e:
            print(f"Fallo crítico, el batch podría perderse o reintentarse: {e}")
            # En sistemas avanzados, aquí enviarías a una "Dead Letter Queue"

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Persister detenido.")