import numpy as np
from numba import njit

# --- 1. CRUCE DE MEDIAS (Optimizado) ---
@njit(fastmath=True, nogil=True, cache=True)
def backtest_ma_crossover(prices, fast_w, slow_w):
    """Calcula PnL total para un par de medias dado un array de precios."""
    n = len(prices)
    if n < slow_w: return 0.0
    
    # Pre-cálculo de medias usando cumsum para velocidad O(1) en ventana móvil
    cumsum = np.cumsum(prices)
    
    # Arrays de medias
    ma_fast = (cumsum[fast_w:] - cumsum[:-fast_w]) / fast_w
    ma_slow = (cumsum[slow_w:] - cumsum[:-slow_w]) / slow_w
    
    # Ajustar índices para alinear (la lenta empieza más tarde)
    offset = slow_w - fast_w
    
    position = 0.0
    pnl = 0.0
    
    # Bucle compilado en C (extremadamente rápido)
    # Iteramos desde el punto donde ambas medias existen
    for i in range(len(ma_slow) - 1):
        # Índices relativos
        idx_price = slow_w + i
        
        # Señal cruce
        f_curr = ma_fast[i + offset]
        s_curr = ma_slow[i]
        f_prev = ma_fast[i + offset - 1]
        s_prev = ma_slow[i - 1]
        
        signal = 0
        if f_prev <= s_prev and f_curr > s_curr: signal = 1   # Golden Cross
        elif f_prev >= s_prev and f_curr < s_curr: signal = -1 # Death Cross
        
        # Ejecución (Simplificada: Entramos al cierre)
        current_price = prices[idx_price]
        next_price = prices[idx_price + 1]
        
        # Retorno logarítmico para PnL acumulado preciso
        if position != 0:
            ret = np.log(next_price / current_price) * position
            pnl += ret
            
        if signal != 0:
            position = signal
            
    return pnl

# --- 2. MOMENTUM (Optimizado) ---
@njit(fastmath=True, nogil=True, cache=True)
def backtest_momentum(prices, period, threshold):
    n = len(prices)
    if n <= period: return 0.0
    
    pnl = 0.0
    position = 0.0
    
    for i in range(period, n - 1):
        curr_price = prices[i]
        prev_price_n = prices[i - period]
        
        if prev_price_n == 0: continue
        
        roc = (curr_price - prev_price_n) / prev_price_n
        
        signal = 0
        if roc > threshold: signal = 1
        elif roc < -threshold: signal = -1
        
        # PnL Calculation
        next_price = prices[i+1]
        if position != 0:
             pnl += np.log(next_price / curr_price) * position
        
        if signal != 0:
            position = signal
            
    return pnl

# --- 3. PATRÓN VELAS (Optimizado) ---
@njit(fastmath=True, nogil=True, cache=True)
def backtest_engulfing(opens, highs, lows, closes, trend_ema):
    """
    Optimiza el patrón envolvente filtrando por tendencia (EMA).
    El parámetro a optimizar es la ventana de la tendencia (trend_ema).
    """
    n = len(closes)
    if n < trend_ema: return 0.0
    
    pnl = 0.0
    position = 0.0
    
    # Calcular EMA simple para tendencia
    alpha = 2 / (trend_ema + 1)
    ema = closes[0]
    
    for i in range(1, n - 1):
        # Actualizar EMA
        ema = alpha * closes[i] + (1 - alpha) * ema
        
        if i < 2: continue
        
        # Detección Patrón
        O1, C1 = opens[i-1], closes[i-1]
        O2, C2 = opens[i], closes[i]
        
        signal = 0
        
        # Bullish Engulfing + Filtro Tendencia Alcista (Precio > EMA)
        if (C1 < O1) and (C2 > O2) and (O2 <= C1) and (C2 >= O1) and (closes[i] > ema):
            signal = 1
            
        # Bearish Engulfing + Filtro Tendencia Bajista (Precio < EMA)
        elif (C1 > O1) and (C2 < O2) and (O2 >= C1) and (C2 <= O1) and (closes[i] < ema):
            signal = -1

        # PnL
        current_price = closes[i]
        next_price = closes[i+1]
        
        if position != 0:
             pnl += np.log(next_price / current_price) * position
             
        # Mantener posición 3 velas (ejemplo) o hasta señal contraria
        # Aquí simplificamos a "hasta señal contraria"
        if signal != 0:
            position = signal

    return pnl