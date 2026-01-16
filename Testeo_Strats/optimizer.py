import sys
import os
import json
import numpy as np
from itertools import product

# Path fixing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.adapters.rest.binance_rest import BinanceRest
from src.core.strategies.math_numba import backtest_ma_crossover, backtest_momentum, backtest_engulfing

PARAMS_FILE = os.path.join(os.path.dirname(__file__), '../src/config/strategy_params.json')

start_date = "2023-01-01"

def get_data(symbol):
    client = BinanceRest()
    # Descargamos suficientes datos (ej. 1000 velas de 1m)
    print(f"📥 Descargando datos para {symbol}...")
    candles = client.get_historical_candles(symbol, "1h", start_str=start_date)
    
    # Extraer numpy arrays (Golden Rule: Typed Arrays)
    opens = np.array([c.open for c in candles], dtype=np.float64)
    highs = np.array([c.high for c in candles], dtype=np.float64)
    lows = np.array([c.low for c in candles], dtype=np.float64)
    closes = np.array([c.close for c in candles], dtype=np.float64)
    return opens, highs, lows, closes

def optimize_ma(closes):
    best_pnl = -np.inf
    best_params = (10, 50)
    
    # Grid Search
    # Fast: 5 a 20 / Slow: 30 a 100
    for f, s in product(range(1, 20, 1), range(20, 200, 10)):
        if 2*f >= s: continue
        pnl = backtest_ma_crossover(closes, f, s)
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = (f, s)
            
    return {"fast": int(best_params[0]), "slow": int(best_params[1]), "pnl": float(best_pnl)}

def optimize_momentum(closes):
    best_pnl = -np.inf
    best_params = (14, 0.001)
    
    # Period: 10 a 30 / Threshold: 0.001 a 0.01
    thresholds = [0.001, 0.005, 0.01]
    for p, t in product(range(10, 31, 2), thresholds):
        pnl = backtest_momentum(closes, p, t)
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = (p, t)
            
    return {"period": int(best_params[0]), "threshold": float(best_params[1]), "pnl": float(best_pnl)}

def optimize_pattern(opens, highs, lows, closes):
    best_pnl = -np.inf
    best_params = (50,) # Trend EMA
    
    # Optimizamos el filtro de tendencia (EMA length)
    for ema_len in range(20, 200, 20):
        pnl = backtest_engulfing(opens, highs, lows, closes, ema_len)
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = (ema_len,)
            
    return {"trend_ema": int(best_params[0]), "pnl": float(best_pnl)}

def main():
    targets = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"] # Tu lista real
    
    final_config = {}

    for symbol in targets:
        print(f"\n--- Optimizando {symbol} ---")
        O, H, L, C = get_data(symbol)
        
        # 1. Medias
        res_ma = optimize_ma(C)
        print(f"   [MA] Mejor: Fast={res_ma['fast']}, Slow={res_ma['slow']} (PnL: {res_ma['pnl']:.4f})")
        
        # 2. Momentum
        res_mom = optimize_momentum(C)
        print(f"   [MOM] Mejor: Period={res_mom['period']}, Thresh={res_mom['threshold']} (PnL: {res_mom['pnl']:.4f})")
        
        # 3. Patrón
        res_pat = optimize_pattern(O, H, L, C)
        print(f"   [PAT] Mejor: TrendEMA={res_pat['trend_ema']} (PnL: {res_pat['pnl']:.4f})")
        
        final_config[symbol] = {
            "MA_CROSS": {"fast": res_ma['fast'], "slow": res_ma['slow']},
            "MOMENTUM": {"period": res_mom['period'], "threshold": res_mom['threshold']},
            "CANDLE_ENGULF": {"trend_ema": res_pat['trend_ema']}
        }

    # Guardar JSON
    os.makedirs(os.path.dirname(PARAMS_FILE), exist_ok=True)
    with open(PARAMS_FILE, 'w') as f:
        json.dump(final_config, f, indent=4)
    print(f"\n✨ Configuración optimizada guardada en {PARAMS_FILE}")

if __name__ == "__main__":
    main()