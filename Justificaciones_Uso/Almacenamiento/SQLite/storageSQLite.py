import sqlite3
import os

class StorageSQLite:
    def __init__(self, db_name='market_data.db'):
        self.db_name = db_name
        # Nota: SQLite crea el archivo si no existe
        self.conn = sqlite3.connect(self.db_name)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        
        # Creamos la tabla con TODAS las columnas
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                time REAL, symbol TEXT, 
                bid_price REAL, bid_quantity REAL, 
                ask_price REAL, ask_quantity REAL, exchange TEXT,
                r REAL, bid REAL, ask REAL, vol REAL, obi REAL
            )
        """)
        
    def write(self, data_list):
        # Usamos nombres de columnas explícitos o diccionarios para evitar errores de orden
        # La forma más segura con diccionarios variables es construir la query dinámicamente o usar pandas
        # Para mantener tu estilo rápido sin pandas aquí:
        keys = data_list[0].keys()
        columns = ', '.join(keys)
        placeholders = ', '.join(':' + k for k in keys)
        sql = f"INSERT INTO ticks ({columns}) VALUES ({placeholders})"
        
        self.conn.executemany(sql, data_list)
        self.conn.commit()

    def get_size(self):
        if os.path.exists(self.db_name):
            return os.path.getsize(self.db_name) / (1024 * 1024)
        return 0