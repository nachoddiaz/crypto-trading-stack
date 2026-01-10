import asyncio
import redis.asyncio as redis
import msgpack
from typing import Any, List

class RedisBus:
    def __init__(self, stream_key: str, redis_url: str = "redis://localhost:6379", group_name: str = None, consumer_name: str = None):
        self.r = redis.from_url(redis_url)
        self.stream_key = stream_key
        self.group_name = group_name
        self.consumer_name = consumer_name
        
    async def initialize(self):
        """Prepara el grupo de consumidores si es necesario (Solo para consumidores)"""
        if self.group_name:
            try:
                # mkstream=True crea el stream si no existe
                await self.r.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise e

    # --- Interfaz compatible con asyncio.Queue para el Productor ---
    async def put(self, item: Any):
        """
        Reemplazo directo de queue.put().
        Golden Rule: Serialización binaria rápida (msgpack) + I/O Asíncrono.
        """
        # Empaquetamos en binario puro para ahorrar ancho de banda y CPU
        data = msgpack.packb(item)
        # maxlen evita que Redis explote la RAM si nadie consume
        await self.r.xadd(self.stream_key, {b'd': data}, maxlen=500000)

    # --- Método optimizado para el Consumidor (Batching) ---
    async def consume_batch(self, batch_size: int = 50, block_ms: int = 1000) -> List[Any]:
        """
        Golden Rule: Avoid repeated calls. Traemos un lote entero de Redis.
        """
        if not self.group_name:
            raise ValueError("Consumer group not defined")

        # Leemos mensajes nuevos ('>')
        entries = await self.r.xreadgroup(
            groupname=self.group_name,
            consumername=self.consumer_name,
            streams={self.stream_key: '>'},
            count=batch_size,
            block=block_ms
        )

        decoded_batch = []
        msg_ids = []

        for stream, messages in entries:
            for msg_id, fields in messages:
                # Golden Rule: Extraer binario y deserializar
                payload = msgpack.unpackb(fields[b'd'])
                decoded_batch.append(payload)
                msg_ids.append(msg_id)

        # ACK implícito o manual. Para máximo rendimiento, podemos hacer ACK aquí
        # o dejar que el persister lo haga tras guardar. 
        # Aquí hacemos ACK simple por lote para limpiar.
        if msg_ids:
            await self.r.xack(self.stream_key, self.group_name, *msg_ids)
            
        return decoded_batch