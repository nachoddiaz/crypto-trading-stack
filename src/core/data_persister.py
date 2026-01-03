import asyncio
import time
from src.database.repository import AsyncRepository

class DataPersister:
    def __init__(self, repository: AsyncRepository, batch_size=50, flush_interval=2):
        self.repo = repository
        self.queue = asyncio.Queue()
        self.batch_size = batch_size      # Guardar cada 50 ticks
        self.flush_interval = flush_interval # O cada 2 segundos (lo que pase primero)
        self._buffer = []

    async def add_metric(self, data: dict):
        """
        Método EXTREMADAMENTE RÁPIDO llamado desde el Hot Path.
        Solo pone el dato en memoria y retorna.
        """
        self.queue.put_nowait(data)

    async def worker(self):
        """
        Proceso de fondo (Consumer) que habla con la DB.
        """
        print("💾 Worker de persistencia iniciado.")
        # Aseguramos que la DB existe
        await self.repo.init_db()
        
        while True:
            try:
                # Lógica de agrupación (Batching)
                start_time = time.time()
                while len(self._buffer) < self.batch_size:
                    # Calculamos cuánto tiempo nos queda antes de forzar el guardado
                    timeout = self.flush_interval - (time.time() - start_time)
                    if timeout <= 0:
                        break
                    
                    try:
                        # Esperamos el siguiente dato con timeout
                        item = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                        self._buffer.append(item)
                        self.queue.task_done()
                    except asyncio.TimeoutError:
                        break # Se acabó el tiempo del intervalo

                # Si tenemos datos, los guardamos
                if self._buffer:
                    await self.repo.save_batch(self._buffer)
                    print(f"✅ DB: Lote de {len(self._buffer)} registros guardado.")
                    self._buffer.clear()
            
            except Exception as e:
                print(f"❌ Error en Persister Worker: {e}")
                await asyncio.sleep(1) # Pausa de seguridad ante errores