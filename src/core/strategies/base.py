import functools
import time
from abc import ABC, abstractmethod, ABCMeta
from typing import Any, Callable, Dict

import numpy as np

# --- DECORADOR: Monitorización de Latencia ---

# Registro global de latencias, indexado por __qualname__ de la función decorada.
# Se acumulan enteros (nanosegundos) para evitar pérdida de precisión en float.
_LATENCY_REGISTRY: Dict[str, Dict[str, int]] = {}


def measure_latency(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Mide el tiempo de ejecución de una función crítica sin alterar su firma.

    El hot path solo paga dos llamadas a ``time.perf_counter_ns()`` y una
    actualización de diccionario (~100 ns), despreciable frente al ciclo de
    estrategia. ``functools.wraps`` preserva ``__name__``, ``__doc__``,
    ``__module__``, ``__qualname__`` y ``__wrapped__``, de modo que la
    introspección y las herramientas de documentación siguen funcionando.

    Las estadísticas acumuladas se leen con :func:`get_latency_stats`.
    """
    key = func.__qualname__
    stats = _LATENCY_REGISTRY.setdefault(key, {"count": 0, "total_ns": 0, "max_ns": 0})

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter_ns()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter_ns() - start
            stats["count"] += 1
            stats["total_ns"] += elapsed
            if elapsed > stats["max_ns"]:
                stats["max_ns"] = elapsed

    return wrapper


def get_latency_stats() -> Dict[str, Dict[str, float]]:
    """
    Devuelve una copia de las latencias acumuladas por función decorada.

    Cada entrada incluye ``count``, ``total_ms``, ``mean_us`` y ``max_us``.
    """
    report: Dict[str, Dict[str, float]] = {}
    for key, s in _LATENCY_REGISTRY.items():
        count = s["count"]
        report[key] = {
            "count": count,
            "total_ms": s["total_ns"] / 1e6,
            "mean_us": (s["total_ns"] / count / 1e3) if count else 0.0,
            "max_us": s["max_ns"] / 1e3,
        }
    return report


def reset_latency_stats() -> None:
    """Pone a cero los contadores. Útil entre ventanas de medición o en tests."""
    for s in _LATENCY_REGISTRY.values():
        s["count"] = 0
        s["total_ns"] = 0
        s["max_ns"] = 0


# --- METACLASE: Validación de Arquitectura ---
class StrategyMeta(ABCMeta):
    """
    Fuerza que todas las estrategias definan un 'ID' único y sigan las reglas del sistema.
    Esto evita errores humanos al crear nuevas estrategias.
    """
    def __new__(cls, name, bases, dct):
        # Ignoramos la clase base abstracta para evitar recursión infinita

        # 1. Creamos la clase usando la lógica de ABC (para soportar abstractmethod)
        new_class = super().__new__(cls, name, bases, dct)
        
        if name == "BaseStrategy":
            return new_class
        
        # Validación 1: Existencia de ID
        if "ID" not in dct:
            raise TypeError(f"❌ Error de Diseño: La estrategia '{name}' debe definir un atributo de clase 'ID'.")
        
        # Validación 2: Convención de Nombres (Mayúsculas)
        strategy_id = dct.get("ID")
        if not isinstance(strategy_id, str) or not strategy_id.isupper():
            raise ValueError(f"❌ Convención: El ID '{strategy_id}' en '{name}' debe ser un string en MAYÚSCULAS.")

        return new_class

# --- CLASE BASE ABSTRACTA ---
class BaseStrategy(ABC, metaclass=StrategyMeta):
    """
    Clase padre de la que deben heredar todas las implementaciones.
    Garantiza compatibilidad con el PortfolioManager.
    """
    def __init__(self):
        pass

    @abstractmethod
    def calculate(self, closes: np.ndarray, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, *args, **kwargs) -> int:
        """
        Método principal que debe implementar la lógica (preferiblemente usando Numba).
        Retorna: 1 (Compra), -1 (Venta), 0 (Neutro)
        """
        pass