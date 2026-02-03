import asyncio
import os
import json
import redis.asyncio as aioredis
from redis.exceptions import ResponseError
import msgpack
from typing import Any, List, AsyncGenerator

# Canal Pub/Sub para broadcasting a WebSockets
PUBSUB_CHANNEL = "live_ticks"

class RedisBus:
    """
    Bus de mensajes Redis con dos modos:
    1. Streams: Para persistencia (garantiza que cada mensaje se procese exactamente una vez)
    2. Pub/Sub: Para broadcasting (envía a todos los suscriptores en tiempo real)
    
    Justificación de Redis para WebSocket:
    - Latencia < 1ms vs 500ms de polling a DB
    - No compite con el persister (canales separados)
    - Escala horizontalmente: múltiples API servers pueden suscribirse
    - Desacopla productores de consumidores
    """
    
    def __init__(self, stream_key: str, redis_url: str = None, group_name: str = None, consumer_name: str = None):
        # Use REDIS_HOST environment variable if available (for Docker)
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        if redis_url is None:
            redis_url = f"redis://{redis_host}:6379"
        self.redis_url = redis_url
        self.r = aioredis.from_url(redis_url)
        self.stream_key = stream_key
        self.group_name = group_name
        self.consumer_name = consumer_name
        self._pubsub = None
        
    async def initialize(self):
        """Prepara el grupo de consumidores si es necesario (Solo para consumidores de Streams)"""
        if self.group_name:
            try:
                await self.r.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
            except ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise e

    # ==================== STREAMS (Persistencia) ====================
    
    async def put(self, item: Any):
        """Envía al Stream para persistencia (procesamiento garantizado)"""
        data = msgpack.packb(item)
        await self.r.xadd(self.stream_key, {b'd': data}, maxlen=500000)

    async def consume_batch(self, batch_size: int = 50, block_ms: int = 1000) -> List[Any]:
        """Consume batch del Stream (para persistencia)"""
        if not self.group_name:
            raise ValueError("Consumer group not defined")

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
                payload = msgpack.unpackb(fields[b'd'])
                decoded_batch.append(payload)
                msg_ids.append(msg_id)

        if msg_ids:
            await self.r.xack(self.stream_key, self.group_name, *msg_ids)
            
        return decoded_batch

    # ==================== PUB/SUB (Broadcasting) ====================
    
    async def publish(self, tick_data: dict):
        """
        Publica tick al canal Pub/Sub para broadcasting a WebSockets.
        Usa JSON porque los clientes WS pueden ser múltiples y diversos.
        """
        await self.r.publish(PUBSUB_CHANNEL, json.dumps(tick_data))
    
    async def subscribe(self) -> AsyncGenerator[dict, None]:
        """
        Suscribe al canal Pub/Sub y genera ticks en tiempo real.
        Usado por la API para enviar a WebSockets.
        """
        pubsub = self.r.pubsub()
        await pubsub.subscribe(PUBSUB_CHANNEL)
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        yield json.loads(message['data'])
                    except json.JSONDecodeError:
                        continue
        finally:
            await pubsub.unsubscribe(PUBSUB_CHANNEL)
            await pubsub.close()