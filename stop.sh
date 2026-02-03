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

# Parar Docker
echo ""
echo "📦 Deteniendo contenedores Docker..."
docker-compose down 2>/dev/null && echo "   ✓ Contenedores detenidos" || echo "   - Docker ya estaba parado"

echo ""
echo "✅ Sistema detenido completamente."
