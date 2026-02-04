#Mantengo histórico inmutable y la vela actual mutable
import numpy as np
from collections import deque
from typing import List, Optional
from .models import Candle, Registro

class MarketState:
    def __init__(self, window_size=1000):
        self.closed_candles: deque = deque(maxlen=window_size)
        self.current_candle: Optional[Candle] = None
        self.interval_sec = 60 # Ejemplo para 1 minuto
        self._history_count = 0  # Contador de velas cargadas via REST (warmup)

    def initialize_history(self, historical_data: List[Candle]):
        """Carga inicial (Cold Path) desde REST API"""
        print(f"⚡ Calentando motor con {len(historical_data)} velas históricas...")
        self.closed_candles.extend(historical_data)
        self._history_count = len(historical_data)  # Guardamos cuántas son históricas
        
        # Inicializar la vela actual basada en el último cierre si es necesario
        # o esperar al primer tick.
        if historical_data:
            last = historical_data[-1]
            # Preparar placeholder para la siguiente vela
            self.current_candle = Candle(
                timestamp=last.timestamp + self.interval_sec * 1000, 
                open=last.close, high=last.close, low=last.close, close=last.close, 
                volume=0.0, closed=False
            )
    
    def get_history_count(self) -> int:
        """Retorna cuántas velas se cargaron via REST (para filtrar warmup)"""
        return self._history_count

    def on_tick(self, tick: Registro):
        """
        HOT PATH: Se ejecuta con cada mensaje del WebSocket.
        Actualiza la vela en construcción o cierra y crea una nueva.
        """
        if not self.current_candle:
            self._start_new_candle(tick)
            return

        # Verificar si la vela actual ya debe cerrarse (Time-based closure)
        # Asumimos timestamps en segundos para coincidir con tu Registro
        tick_time_ms = tick.time * 1000
        candle_start_ms = self.current_candle.timestamp
        
        if tick_time_ms >= (candle_start_ms + self.interval_sec * 1000):
            self._close_current_candle()
            self._start_new_candle(tick)
        else:
            self._update_candle(tick)

    def _update_candle(self, tick: Registro):
        """Operación ligera de actualización (in-place)"""
        c = self.current_candle
        c.close = tick.bid_price # O mid price, según tu lógica
        if c.close > c.high: 
            c.high = c.close
        if c.close < c.low: 
            c.low = c.close
        c.volume += (tick.bid_quantity + tick.ask_quantity) # Aproximación de volumen

    def _close_current_candle(self):
        """Promueve la vela actual a histórico inmutable"""
        self.current_candle.closed = True
        self.closed_candles.append(self.current_candle) # O(1)

    def add_candle(self, candle: Candle):
        """
        Agrega una vela cerrada externamente (desde BBDD o RealTimeProcessor).
        """
        self.closed_candles.append(candle)
    
    def _start_new_candle(self, tick: Registro):
        """Reinicia el objeto vela actual (evitamos allocar si podemos reusar, pero por claridad creamos nuevo)"""
        # Para cumplir strict golden rules, podríamos tener 2 objetos y hacer swap, 
        # pero instanciar una dataclass es rápido.
        price = tick.bid_price
        # Alineamos el timestamp al inicio del minuto/hora
        aligned_time = (int(tick.time) // self.interval_sec) * self.interval_sec * 1000
        
        self.current_candle = Candle(
            timestamp=aligned_time,
            open=price, high=price, low=price, close=price,
            volume=0, closed=False
        )

    def get_arrays(self):
        """
        Golden Rule: Zero-copy views o conversiones masivas eficientes.
        Devuelve arrays numpy para el cálculo vectorizado de indicadores.
        """
        # Convertir deque a list es rápido, y list a numpy es optimizado en C
        # Esto se hace SOLO cuando se necesita recalcular estrategia, no en cada tick.
        data = list(self.closed_candles)
        closes = np.array([c.close for c in data], dtype=np.float64)
        # Añadimos el precio actual "live" al final para indicadores que repintan en tiempo real
        if self.current_candle:
             closes = np.append(closes, self.current_candle.close)
        return closes

    def get_ohlc_arrays(self):
        """
        Devuelve las 4 series OHLC como arrays numpy para estrategias que necesitan
        más que solo closes (ej: patrones de velas, volatilidad).
        """
        data = list(self.closed_candles)
        if not data:
            return None, None, None, None
        
        opens = np.array([c.open for c in data], dtype=np.float64)
        highs = np.array([c.high for c in data], dtype=np.float64)
        lows = np.array([c.low for c in data], dtype=np.float64)
        closes = np.array([c.close for c in data], dtype=np.float64)
        
        # Añadimos la vela actual "live" al final
        if self.current_candle:
            opens = np.append(opens, self.current_candle.open)
            highs = np.append(highs, self.current_candle.high)
            lows = np.append(lows, self.current_candle.low)
            closes = np.append(closes, self.current_candle.close)
        
        return opens, highs, lows, closes
