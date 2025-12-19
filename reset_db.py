import os
from sqlalchemy import create_engine, text

# 1. Borrar SQLite (Simplemente borramos el archivo)
if os.path.exists("live_bench.db"):
    os.remove("live_bench.db")
    print("✅ SQLite reseteado (Archivo borrado)")

# 2. Borrar Tabla PostgreSQL
PG_URI = "postgresql://postgres:password@localhost:5432/finance_bench"
try:
    engine = create_engine(PG_URI)
    with engine.connect() as con:
        con.execute(text("DROP TABLE IF EXISTS ticks CASCADE;"))
        con.commit()
    print("✅ PostgreSQL reseteado (Tabla 'ticks' borrada)")
except Exception as e:
    print(f"❌ Error borrando Postgres: {e}")

print("\n🚀 Ahora ejecuta benchmark_live.py de nuevo.")