import asyncio
import time
from dataclasses import asdict

# --- TUS IMPORTS DE LÓGICA ---
from sockets_Binance import BinanceDriver
from reserve_price import ReservePrice
from models import Registro

# --- TUS IMPORTS DE ALMACENAMIENTO ---
# Asegúrate de que las rutas sean correctas según tu estructura de carpetas
from Justificaciones_Uso.Almacenamiento.CSVSto import StorageCSV
from Justificaciones_Uso.Almacenamiento.SQLite import StorageSQLite
from Justificaciones_Uso.Almacenamiento.Parquet import StorageParquet
from Justificaciones_Uso.Almacenamiento.PostgreSQL import StoragePostgres
from Justificaciones_Uso.Almacenamiento.MongoDB import StorageMongo

# --- CONFIGURACIÓN ---
BUFFER_SIZE = 100  # Acumular 100 ticks antes de escribir (Crucial para rendimiento real)
PG_URI = "postgresql://postgres:password@localhost:5432/finance_bench"
MONGO_URI = "mongodb://localhost:27017/"

class LiveBenchmarkEngine:
    def __init__(self):
        # 1. Inicializar Motores de Almacenamiento
        print("🛠 Inicializando Motores de Base de Datos...")
        self.strategies = [
            ("CSV", StorageCSV(filename='live_bench.csv')),
            ("SQLite", StorageSQLite(db_name='live_bench.db')),
            ("Parquet", StorageParquet(filename='live_bench.parquet')),
            ("PostgreSQL", StoragePostgres(PG_URI)),
            ("MongoDB", StorageMongo(MONGO_URI))
        ]
        
        # 2. Inicializar Lógica Financiera
        self.pricer = ReservePrice()
        
        # 3. Buffer en Memoria
        self.buffer = []

    async def process_tick(self, tick: Registro):
        """
        Recibe un tick limpio del socket, calcula el precio de reserva
        y lo agrega al buffer de escritura.
        """
        # A. CÁLCULO FINANCIERO (Reserve Price)
        # Usamos tu lógica existente
        calc_result = self.pricer._calc_reservation_price(tick)
        
        # Si no hay resultado (ej. iniciando volatilidad), ignoramos o guardamos nulos
        if not calc_result:
            return

        # B. FUSIÓN DE DATOS
        # Combinamos los datos crudos del tick con los cálculos del modelo
        # Convertimos el dataclass a diccionario
        full_record = asdict(tick) 
        
        # Agregamos los cálculos (r, bid, ask, vol, obi)
        full_record.update(calc_result)
        
        # Agregamos al buffer
        self.buffer.append(full_record)

        # C. TRIGGER DE ESCRITURA (Cuando el buffer se llena)
        if len(self.buffer) >= BUFFER_SIZE:
            await self._flush_to_storage()

    async def _flush_to_storage(self):
        """Envía el buffer a todos los almacenamientos y mide tiempos"""
        print(f"\n⚡ Buffer lleno ({len(self.buffer)} ticks). Escribiendo...")
        
        for name, engine in self.strategies:
            # Validaciones de conexión
            if name == "PostgreSQL" and getattr(engine, 'engine', None) is None: 
                continue
            if name == "MongoDB" and getattr(engine, 'client', None) is None: 
                continue

            try:
                # --- MEDICIÓN DE TIEMPO ---
                start_time = time.time()
                
                # Escritura (Nota: .write suele ser síncrono en tus clases, 
                # bloqueando brevemente el loop. En HFT real usaríamos run_in_executor)
                engine.write(self.buffer)
                
                duration = time.time() - start_time
                # --------------------------

                # Métricas rápidas
                ticks_per_sec = int(BUFFER_SIZE / duration) if duration > 0 else 0
                print(f"  > {name:<12} | ⏱ {duration:.4f}s | 🚀 {ticks_per_sec} ticks/s")

            except Exception as e:
                print(f"  ❌ Error en {name}: {e}")

        # Limpiar buffer para los siguientes datos
        self.buffer = []
        print("-" * 50)

async def main():
    # 1. Crear la tubería
    queue = asyncio.Queue()
    
    # 2. Instanciar el Benchmark
    benchmark = LiveBenchmarkEngine()
    
    # 3. Instanciar el Driver de Binance
    driver = BinanceDriver(queue)
    symbol = "btcusdt"

    print(f"🚀 INICIANDO SISTEMA: Socket {symbol.upper()} -> ReservePrice -> Storage")

    # 4. Lanzar tareas en paralelo
    # Tarea A: Socket Productor (Binance -> Queue)
    producer_task = asyncio.create_task(driver.subscribe(symbol))
    
    # Tarea B: Consumidor (Queue -> Process -> Storage)
    async def consumer_loop():
        while True:
            tick = await queue.get()
            await benchmark.process_tick(tick)
            queue.task_done()

    consumer_task = asyncio.create_task(consumer_loop())

    # Mantener vivo
    await asyncio.gather(producer_task, consumer_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido.")