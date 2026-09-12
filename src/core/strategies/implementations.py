import numpy as np

# Importamos la lógica dura (los pistones)
# Asegúrate de que math_numba exista en src/core/
from src.core.strategies import math_numba 
from src.core.strategies.base import BaseStrategy, measure_latency

class MACrossover(BaseStrategy):
    ID = "MA_CROSS"

    def __init__(self, fast_period: int, slow_period: int):
        # Configuración (Cold Path): Se ejecuta una sola vez al inicio
        self.fast = int(fast_period)
        self.slow = int(slow_period)

    @measure_latency
    def calculate(self, closes: np.ndarray, **kwargs) -> int:
        """ Delegamos a Numba para señal de cruce de medias."""
        return math_numba.calc_ma_signal(closes, self.fast, self.slow)

class MomentumStrategy(BaseStrategy):
    ID = "MOMENTUM"
    def __init__(self, period: int, threshold: float):
        self.period = int(period)
        self.threshold = float(threshold)

    @measure_latency
    def calculate(self, closes: np.ndarray, **kwargs) -> int:
        return math_numba.calc_momentum_signal(closes, self.period, self.threshold)

class EngulfingPattern(BaseStrategy):
    ID = "ENGULFING"
    def __init__(self):
        pass

    @measure_latency
    def calculate(self, closes: np.ndarray, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> int:
        return math_numba.calc_engulfing_signal(opens, highs, lows, closes)