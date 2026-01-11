import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.redis_bus import RedisBus
from src.database.repository import AsyncRepository
from src.core.data_persister import DataPersister

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

    print("--- Persister Iniciado: Escuchando Redis ---")

    # 3. El Bucle Infinito (The Event Loop)
    while True:
        # A. Extraer (I/O Wait eficiente)
        # batch_size=50 cumple tu regla de batching
        # block_ms=2000 evita loops vacíos (CPU friendly)
        raw_batch = await bus.consume_batch(batch_size=50, block_ms=2000)
        
        if not raw_batch:
            continue

        # B. Procesar y Guardar (Hot Path)
        try:
            await persister.save_batch(raw_batch)
        except Exception as e:
            print(f"Fallo crítico, el batch podría perderse o reintentarse: {e}")
            # En sistemas avanzados, aquí enviarías a una "Dead Letter Queue"

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Persister detenido.")