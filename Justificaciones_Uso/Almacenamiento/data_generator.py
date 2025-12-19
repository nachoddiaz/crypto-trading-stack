# data_generator.py
import json
import random
import time
from models import Registro

NUM_RECORDS = 10_000_000

def generate_dataset():
    print(f"Generando {NUM_RECORDS} registros simulados...")
    data = []
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'EURUSD']
    base_time = time.time()

    for i in range(NUM_RECORDS):
        mid = random.uniform(100, 60000)
        spread = mid * 0.0001
        
        # Creamos diccionarios directos para facilitar serialización JSON
        record = {
            "time": base_time + (i * 0.01),
            "symbol": random.choice(symbols),
            "bid_price": round(mid - spread, 2),
            "bid_quantity": round(random.uniform(0.01, 2.5), 4),
            "ask_price": round(mid + spread, 2),
            "ask_quantity": round(random.uniform(0.01, 2.5), 4),
            "exchange": "Binance"
        }
        data.append(record)
    # Guardar en disco para que todos los motores usen EXACTAMENTE los mismos datos
    with open("dataset.json", "w") as f:
        json.dump(data, f)
    
    print("✅ dataset.json creado exitosamente.")

if __name__ == "__main__":
    generate_dataset()