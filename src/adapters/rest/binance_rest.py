import requests
import pandas as pd
from datetime import datetime

def get_historical_data(symbol: str, interval, limit = 1000):
    url = "https://api.binance.com/api/v3/klines"
    
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    response = requests.get(url, params=params)
    data = response.json() 

    #Binance devuelve una lista de listas, lo pasamos a DF
    df = pd.DataFrame(data)
    #Queremos quedarnos sólo con las primeras 6 (open time, open, high, low, close and volume)
    df = df.iloc[:, :6]
    df.columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    #Binance devuelve precios y volúmenes en formato string, hay que pasarlo a float
    df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
    #Binance devuelve open time en ms, hay que convertirlo a datetime
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')

    return df
    