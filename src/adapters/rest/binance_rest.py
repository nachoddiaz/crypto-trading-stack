import requests
import pandas as pd
from datetime import datetime
from typing import List
from src.core.models import Candle

class BinanceRest:
    def get_historical_candles(self, symbol: str, interval: str, limit=1000) -> List[Candle]:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            candles = []
            for row in data:
                # row structure: [Open Time, Open, High, Low, Close, Volume, Close Time, ...]
                c = Candle(
                    timestamp=int(row[0]), # Keep as int ms
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    closed=True
                )
                candles.append(c)
            
            return candles
            
        except Exception as e:
            print(f"Error descargando histórico para {symbol}: {e}")
            return []