import numpy as np
import numba as nb
from numba import njit

# --- 1. CRUCE DE MEDIAS (Optimizado) ---
@njit(fastmath=True, nogil=True, cache=True)
def backtest_ma_crossover(prices, fast_w, slow_w):
    """Calcula PnL total para un par de medias dado un array de precios."""
    n = len(prices)
    if n < slow_w: 
        return 0.0
    
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
        if f_prev <= s_prev and f_curr > s_curr: 
            signal = 1   # Golden Cross
        elif f_prev >= s_prev and f_curr < s_curr: 
            signal = -1 # Death Cross
        
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

# --- 1.1 SEÑAL MA CROSSOVER (TIEMPO REAL) ---
@njit(fastmath=True, cache=True)
def calc_ma_signal(prices: np.ndarray, fast_w: int, slow_w: int) -> int:
    """
    HOT PATH: Calcula señal de cruce de medias SOLO en las últimas 2 velas.
    Retorna: +1 (comprar), -1 (vender), 0 (neutral)
    """
    n = len(prices)
    if n < slow_w + 1:
        return 0  # No hay suficientes datos
    
    # Calcular MAs usando los últimos datos
    # MA actual (última vela)
    fast_ma_curr = np.mean(prices[-fast_w:])
    slow_ma_curr = np.mean(prices[-slow_w:])
    
    # MA anterior (penúltima vela)
    fast_ma_prev = np.mean(prices[-(fast_w+1):-1])
    slow_ma_prev = np.mean(prices[-(slow_w+1):-1])
    
    # Detección de cruce
    # Golden Cross: MA rápida cruza ARRIBA de la lenta
    if fast_ma_prev <= slow_ma_prev and fast_ma_curr > slow_ma_curr:
        return 1  # BUY
    
    # Death Cross: MA rápida cruza ABAJO de la lenta
    if fast_ma_prev >= slow_ma_prev and fast_ma_curr < slow_ma_curr:
        return -1  # SELL
    
    return 0  # Sin cruce


# --- 2. MOMENTUM (Optimizado) ---
@njit(fastmath=True, nogil=True, cache=True)
def backtest_momentum(prices, period, threshold):
    n = len(prices)
    if n <= period: 
        return 0.0
    
    pnl = 0.0
    position = 0.0
    
    for i in range(period, n - 1):
        curr_price = prices[i]
        prev_price_n = prices[i - period]
        
        if prev_price_n == 0: 
            continue
        
        roc = (curr_price - prev_price_n) / prev_price_n
        
        signal = 0
        if roc > threshold: 
            signal = 1
        elif roc < -threshold: 
            signal = -1
        
        # PnL Calculation
        next_price = prices[i+1]
        if position != 0:
             pnl += np.log(next_price / curr_price) * position
        
        if signal != 0:
            position = signal
            
    return pnl

# --- 2.1 SEÑAL MOMENTUM (TIEMPO REAL) ---
@njit(fastmath=True, cache=True)
def calc_momentum_signal(prices: np.ndarray, period: int, threshold: float) -> int:
    """
    HOT PATH: Calcula señal de momentum (ROC) en la última vela.
    Retorna: +1 (comprar), -1 (vender), 0 (neutral)
    """
    n = len(prices)
    if n <= period:
        return 0  # No hay suficientes datos
    
    curr_price = prices[-1]
    prev_price = prices[-period - 1]
    
    if prev_price == 0:
        return 0
    
    # Rate of Change (ROC)
    roc = (curr_price - prev_price) / prev_price
    
    # Señal según umbral
    if roc > threshold:
        return 1  # BUY - Momentum alcista fuerte
    elif roc < -threshold:
        return -1  # SELL - Momentum bajista fuerte
    
    return 0  # Neutral

@njit(fastmath=True, nogil=True, cache=True)
def backtest_engulfing(opens, highs, lows, closes, trend_ema):

    """
    Optimiza el patrón envolvente filtrando por tendencia (EMA).
    El parámetro a optimizar es la ventana de la tendencia (trend_ema).
    """
    n = len(closes)
    if n < trend_ema: 
        return 0.0
    
    pnl = 0.0
    position = 0.0
    
    # Calcular EMA simple para tendencia
    alpha = 2 / (trend_ema + 1)
    ema = closes[0]
    
    for i in range(1, n - 1):
        # Actualizar EMA
        ema = alpha * closes[i] + (1 - alpha) * ema
        
        if i < 2: 
            continue
        
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

# 3.1 Calcula patrón Engulfing SOLO en la última vela cerrada.
nb.jit(nopython=True, cache=True)
def calc_engulfing_signal(opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> int:
    """
    HOT PATH: Calcula patrón Engulfing SOLO en la última vela cerrada.
    Argumentos: 4 arrays (opens, highs, lows, closes)
    Retorna: int (-1 venta, 1 compra, 0 nada)
    """
    # Necesitamos al menos 2 velas para un patrón de 2 velas
    if len(closes) < 2:
        return 0
    
    # Índices: -1 es la última vela cerrada, -2 es la anterior
    # Vela actual (Signal Candle)
    curr_open = opens[-1]
    curr_close = closes[-1]
    
    # Vela anterior (Setup Candle)
    prev_open = opens[-2]
    prev_close = closes[-2]
    
    # Lógica Bullish Engulfing (Envolvente Alcista)
    # 1. Vela anterior fue roja (bajista)
    prev_is_red = prev_close < prev_open
    # 2. Vela actual es verde (alcista)
    curr_is_green = curr_close > curr_open
    # 3. El cuerpo actual envuelve al cuerpo anterior
    engulfs = (curr_open <= prev_close) and (curr_close >= prev_open)
    
    if prev_is_red and curr_is_green and engulfs:
        return 1

    # Lógica Bearish Engulfing (Envolvente Bajista)
    # 1. Vela anterior fue verde
    prev_is_green = prev_close > prev_open
    # 2. Vela actual es roja
    curr_is_red = curr_close < curr_open
    # 3. El cuerpo actual envuelve al anterior
    engulfs_bear = (curr_open >= prev_close) and (curr_close <= prev_open)
    
    if prev_is_green and curr_is_red and engulfs_bear:
        return -1
        
    return 0