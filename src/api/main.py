import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.infrastructure.redis_bus import RedisBus

app = FastAPI(title="Hesperides Crypto Trading API", version="1.0.0")

# --- 1. Configuración CORS (CRÍTICO PARA REACT) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"], # 5173 es el puerto default de Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas REST
app.include_router(router, prefix="/api")

# --- 2. Endpoint WebSocket (Tiempo Real) ---
# El Frontend se conectará aquí para recibir precios y PnL en vivo
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Conectamos a Redis para escuchar lo que publica el Ingestor/Engine
    bus = RedisBus(stream_key="binance_ticks")
    await bus.initialize()
    
    try:
        while True:
            # Leemos de Redis (simulado consumo directo o pub/sub)
            # En un caso real usaríamos un canal PUB/SUB de Redis, no Streams, para broadcasting
            # Aquí simulamos datos para que veas el flow:
            
            # TODO: Conectar esto al canal real de eventos del TraderEngine
            fake_update = {
                "type": "TICK",
                "symbol": "BTCUSDT",
                "price": 50000.0 + (asyncio.get_event_loop().time() % 10),
                "timestamp": asyncio.get_event_loop().time() * 1000
            }
            
            await websocket.send_json(fake_update)
            await asyncio.sleep(1) # Throttle para no saturar el navegador
            
    except WebSocketDisconnect:
        print("Cliente desconectado")
    except Exception as e:
        print(f"Error WS: {e}")

# --- 3. Eventos de Inicio/Apagado ---
@app.on_event("startup")
async def startup_event():
    print("🚀 API Iniciada. Swagger en http://localhost:8000/docs")

if __name__ == "__main__":
    import uvicorn
    # Hot reload activado para desarrollo
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)