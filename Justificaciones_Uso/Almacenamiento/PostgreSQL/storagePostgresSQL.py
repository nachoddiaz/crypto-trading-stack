from sqlalchemy import create_engine, text
import pandas as pd

class StoragePostgres:
    def __init__(self, uri):
        self.engine = create_engine(uri)
        try:
            with self.engine.connect() as con:
                con.execute(text("SET synchronous_commit = OFF;"))
                # ⚠️ IMPORTANTE: En producción no haríamos DROP cada vez, 
                # pero para que se actualice tu esquema ahora, descomenta esta línea una vez:
                # con.execute(text("DROP TABLE IF EXISTS ticks"))
                
                con.execute(text("""
                    CREATE TABLE IF NOT EXISTS ticks (
                        time DOUBLE PRECISION, 
                        symbol TEXT, 
                        
                        -- Datos Crudos del Socket
                        bid_price DOUBLE PRECISION, 
                        bid_quantity DOUBLE PRECISION, 
                        ask_price DOUBLE PRECISION, 
                        ask_quantity DOUBLE PRECISION, 
                        exchange TEXT,
                        
                        -- NUEVOS CAMPOS (Lógica Financiera)
                        r DOUBLE PRECISION,       -- Precio Reserva
                        bid DOUBLE PRECISION,     -- Bid Calculado (Final)
                        ask DOUBLE PRECISION,     -- Ask Calculado (Final)
                        vol DOUBLE PRECISION,     -- Volatilidad
                        obi DOUBLE PRECISION      -- Imbalance
                    )
                """))
                
                # Intentar convertir a Hypertable (TimescaleDB) si no lo es
                con.execute(text("SELECT create_hypertable('ticks', 'time', if_not_exists => TRUE);"))
                con.commit()
                
        except Exception as e:
            print(f"Postgres Error: {e}")
            self.engine = None

    def write(self, data_list):
        if not self.engine: 
            return
        df = pd.DataFrame(data_list)
        df.to_sql('ticks', self.engine, if_exists='append', index=False, method='multi')

    def get_size(self):
        if not self.engine: 
            return 0
        with self.engine.connect() as con:
            return con.execute(text("SELECT pg_total_relation_size('ticks')")).scalar() / (1024 * 1024)