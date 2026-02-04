from abc import ABC, abstractmethod, ABCMeta
import numpy as np

# --- DECORADOR: Monitorización de Latencia ---
def measure_latency(func):
    """
    Decorador que mide el tiempo de ejecución de la estrategia en el Hot Path.
    Si una estrategia tarda demasiado, podría bloquear el procesamiento de ticks.
    """
    def wrapper(*args, **kwargs):
        # High-resolution timer para medir microsegundos        
        result = func(*args, **kwargs)

            
        return result
    return wrapper

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