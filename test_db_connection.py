import asyncio
import sys
import os
import time
import random

# Asegura que encuentra los módulos
sys.path.append(os.path.abspath(os.getcwd()))

from src.database.repository import AsyncRepository

async def test_database_flow():
    print("🧪 INICIANDO TEST DE BASE DE DATOS...")

    # 1. Instanciar Repositorio
    repo = AsyncRepository()

    # 2. Inicializar Tablas
    try:
        await repo.init_db()
    except Exception as e:
        print(f"❌ Error conectando a DB: {e}")
        print("💡 Pista: ¿Está Docker corriendo? ¿La password es correcta?")
        return

    # 3. Crear Datos Falsos (Simulando lo que envía el Core)
    fake_batch = []
    symbol = "BTCUSDT"
    
    print("📝 Generando datos de prueba...")
    for i in range(10):
        fake_tick = {
            'symbol': symbol,
            'time': time.time() + i, # Incrementamos tiempo
            'bid_price': 50000.0 + random.uniform(-10, 10),
            'ask_price': 50001.0 + random.uniform(-10, 10),
            'bid_quantity': random.uniform(0.1, 2.0),
            'ask_quantity': random.uniform(0.1, 2.0),
            'reservation_price': 50000.5,
            'vol': 0.002
        }
        fake_batch.append(fake_tick)

    # 4. Guardar Batch
    print(f"💾 Guardando batch de {len(fake_batch)} elementos...")
    start = time.time()
    await repo.save_batch(fake_batch)
    end = time.time()
    print(f"✅ Guardado exitoso en {end - start:.4f} segundos.")

    # 5. Verificar (Leer lo que acabamos de escribir)
    print("🔍 Leyendo datos desde la DB para verificar...")
    stored_ticks = await repo.get_latest_ticks(symbol, limit=3)
    
    if stored_ticks:
        print(f"\n--- Últimos 3 registros en DB para {symbol} ---")
        for tick in stored_ticks:
            print(f"ID: {tick.id} | Time: {tick.exchange_time} | Price: {tick.bid_price} | ResPrice: {tick.reservation_price}")
        print("\n✅ TEST SUPERADO: Los datos entran y salen correctamente.")
    else:
        print("\n❌ TEST FALLIDO: No se encontraron datos.")

if __name__ == "__main__":
    asyncio.run(test_database_flow())