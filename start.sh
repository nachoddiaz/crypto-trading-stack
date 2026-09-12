#!/bin/bash
# ============================================
# Crypto Trading Stack - Script de Inicio
# ============================================

set -e  # Detener si hay error

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 Iniciando Crypto Trading Stack..."

# 1. Levantar infraestructura Docker
echo ""
echo "📦 Paso 1/4: Levantando Docker (PostgreSQL, Redis, API)..."
docker-compose up -d

# Esperar a que PostgreSQL y Redis estén listos
echo "⏳ Esperando a que los servicios estén listos..."
sleep 5

# Activar entorno virtual
source .venv/bin/activate

# 2. Ejecutar persister en background (GUARDA LOS TICKS EN DB)
echo ""
echo "💾 Paso 2/4: Iniciando Persister (guarda ticks en DB)..."
python apps/persister.py &
PERSISTER_PID=$!
echo "   Persister PID: $PERSISTER_PID"
sleep 2

# 3. Ejecutar ingestor en background (DESCARGA DATOS + WEBSOCKET)
echo ""
echo "📥 Paso 3/4: Iniciando Ingestor (REST + WebSocket)..."
python apps/ingestor.py &
INGESTOR_PID=$!
echo "   Ingestor PID: $INGESTOR_PID"

# 4. Levantar frontend en modo desarrollo
echo ""
echo "🌐 Paso 4/4: Iniciando Frontend (dev mode)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
cd ..

echo ""
echo "============================================"
echo "✅ Sistema iniciado correctamente!"
echo ""
echo "📊 Dashboard: http://localhost:5173"
echo "🔌 API:       http://localhost:8000"
echo ""
echo "PIDs de los procesos:"
echo "  Persister: $PERSISTER_PID"
echo "  Ingestor:  $INGESTOR_PID"
echo "  Frontend:  $FRONTEND_PID"
echo ""
echo "Para detener todo: Ctrl+C, luego:"
echo "  docker-compose down"
echo "============================================"

# Trap para limpiar al salir
trap "kill $PERSISTER_PID $INGESTOR_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Esperar a que los procesos terminen (o Ctrl+C)
wait
