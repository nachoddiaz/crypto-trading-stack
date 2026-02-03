import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.infrastructure.redis_bus import RedisBus

app = FastAPI(title="Hesperides Crypto Trading API", version="1.0.0")

# --- 1. Configuración CORS (CRÍTICO PARA REACT) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas REST
app.include_router(router, prefix="/api")

# --- 2. Endpoint WebSocket (Tiempo Real via Redis Pub/Sub) ---
# Justificación de Redis Pub/Sub:
# - Latencia < 1ms (vs 500ms polling DB)
# - No compite con persister (canales separados)
# - Escala horizontalmente: múltiples API servers pueden suscribirse
# - Desacopla productores (ingestor) de consumidores (WebSocket clients)
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Conectamos a Redis Pub/Sub
    bus = RedisBus(stream_key="binance_ticks")
    
    try:
        # Suscribirse y enviar cada mensaje al cliente WebSocket
        async for tick in bus.subscribe():
            await websocket.send_json(tick)
                
    except WebSocketDisconnect:
        print("Cliente WebSocket desconectado")
    except Exception as e:
        print(f"Error WS: {e}")

# --- 3. Eventos de Inicio/Apagado ---
@app.on_event("startup")
async def startup_event():
    print("🚀 API Iniciada. Swagger en http://localhost:8000/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)