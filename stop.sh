#!/bin/bash
# ============================================
# Hesperides Trading System - Script de Parada
# ============================================

echo "🛑 Deteniendo Hesperides Trading System..."

# Matar procesos Python
pkill -f "python apps/ingestor.py" 2>/dev/null && echo "   ✓ Ingestor detenido" || echo "   - Ingestor no estaba corriendo"
pkill -f "python apps/persister.py" 2>/dev/null && echo "   ✓ Persister detenido" || echo "   - Persister no estaba corriendo"

# Matar frontend
pkill -f "npm run dev" 2>/dev/null && echo "   ✓ Frontend detenido" || echo "   - Frontend no estaba corriendo"
pkill -f "vite" 2>/dev/null

# Limpiar base de datos (ticks, candles, trades) - solo si el contenedor está corriendo
echo ""
echo "🗑️  Limpiando base de datos..."
if docker ps --format '{{.Names}}' | grep -q "postgres_db"; then
    # Dar un momento para que el contenedor esté listo
    sleep 0.5
    # Limpiar tablas individualmente para mejor manejo de errores (suprimiendo output de psql)
    docker exec postgres_db psql -U postgres -d postgres_db -c "TRUNCATE TABLE ticks RESTART IDENTITY CASCADE;" &>/dev/null && echo "   ✓ Tabla ticks limpiada" || echo "   - Tabla ticks vacía/no existe"
    docker exec postgres_db psql -U postgres -d postgres_db -c "TRUNCATE TABLE candles RESTART IDENTITY CASCADE;" &>/dev/null && echo "   ✓ Tabla candles limpiada" || echo "   - Tabla candles vacía/no existe"
    docker exec postgres_db psql -U postgres -d postgres_db -c "TRUNCATE TABLE trades RESTART IDENTITY CASCADE;" &>/dev/null && echo "   ✓ Tabla trades limpiada" || echo "   - Tabla trades vacía/no existe"
else
    echo "   - Contenedor postgres_db no está corriendo, omitiendo limpieza"
fi

# Parar Docker
echo ""
echo "📦 Deteniendo contenedores Docker..."
docker-compose down 2>/dev/null && echo "   ✓ Contenedores detenidos" || echo "   - Docker ya estaba parado"

echo ""
echo "✅ Sistema detenido completamente."
