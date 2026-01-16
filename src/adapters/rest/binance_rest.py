import time
import requests
import logging
from typing import List, Optional
from datetime import datetime
from src.core.models import Candle

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BinanceRest:
    def __init__(self):
        self.base_url = "https://api.binance.com"

    def _make_request(self, endpoint: str, params: dict) -> Optional[list]:
        """
        Realiza la petición HTTP manejando Rate Limits y Errores de Servidor.
        """
        url = self.base_url + endpoint
        
        while True:
            try:
                response = requests.get(url, params=params, timeout=10)
                
                # 1. Éxito
                if response.status_code == 200:
                    return response.json()
                
                # 2. Rate Limits (429) - Calmarse
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"⚠️ 429 Rate Limit. Durmiendo {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                # 3. IP Ban (418) - Peligro
                elif response.status_code == 418:
                    retry_after = int(response.headers.get("Retry-After", 300))
                    logger.error(f"🛑 418 IP BANNED. Durmiendo {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                # 4. Errores de Servidor (5xx)
                elif 500 <= response.status_code < 600:
                    logger.warning(f"Error Servidor Binance ({response.status_code}). Reintentando en 5s...")
                    time.sleep(5)
                    continue

                else:
                    logger.error(f"Error HTTP {response.status_code}: {response.text}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Error de conexión: {e}. Reintentando en 5s...")
                time.sleep(5)

    def get_historical_candles(self, symbol: str, interval: str, start_str: str = "2020-01-01") -> List[Candle]:
        """
        Descarga TODA la historia disponible desde 'start_str' hasta AHORA.
        Usa paginación por 'startTime' (hacia adelante).
        
        :param start_str: Fecha de inicio formato 'YYYY-MM-DD'
        """
        endpoint = "/api/v3/klines"
        limit_per_call = 1000
        all_candles = []
        
        # Convertir fecha inicio a timestamp ms
        start_ts = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
        # Timestamp actual
        end_ts_now = int(time.time() * 1000)
        
        current_start = start_ts
        
        logger.info(f"📥 Iniciando descarga masiva para {symbol} desde {start_str}...")

        while True:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit_per_call,
                'startTime': current_start
            }
            
            data = self._make_request(endpoint, params)
            
            if not data:
                break
                
            # Procesar lote
            batch_candles = []
            last_close_time = 0
            
            for row in data:
                # Filtrar velas que se pasen del tiempo actual (por si acaso)
                if row[0] > end_ts_now:
                    break

                c = Candle(
                    timestamp=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    closed=True # Asumimos cerradas si son históricas
                )
                batch_candles.append(c)
                last_close_time = row[6] # Index 6 es Close Time en Binance
            
            if not batch_candles:
                break
                
            all_candles.extend(batch_candles)
            logger.info(f"   -> Descargadas {len(batch_candles)} velas. Total acumulado: {len(all_candles)}. Última fecha: {datetime.fromtimestamp(last_close_time/1000)}")
            
            # Condición de salida: Si el lote recibido es menor al límite, hemos llegado al final
            if len(data) < limit_per_call:
                break
                
            # Actualizar cursor: StartTime será el tiempo de cierre de la última vela + 1ms
            current_start = last_close_time + 1
            
            # Si nos pasamos del tiempo actual, salir
            if current_start > end_ts_now:
                break
                
            # Rate Limiting Preventivo (Importante)
            time.sleep(0.15) 

        logger.info(f"✅ Descarga completada. Total velas: {len(all_candles)}")
        return all_candles

# --- Bloque de prueba (solo se ejecuta si corres este script directamente) ---
if __name__ == "__main__":
    client = BinanceRest()
    # Ejemplo: Descargar datos desde 2023 hasta hoy
    history = client.get_historical_candles("BTCUSDT", "1h", start_str="2023-01-01")
    print(f"Primera vela: {history[0].timestamp}")
    print(f"Última vela: {history[-1].timestamp}")