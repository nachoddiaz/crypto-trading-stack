from dataclasses import dataclass, field
from typing import Optional

@dataclass(slots=True)
class Registro:
    # Usamos slots=True para reducir memoria y acelerar acceso (Golden Rule)
    exchange: str
    symbol: str
    time: float
    bid_price: float
    bid_quantity: float
    ask_price: float
    ask_quantity: float

    def to_dict(self):
        """Serialización manual ultra-rápida para el Hot Path."""
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "time": self.time,
            "bid_price": self.bid_price,
            "bid_quantity": self.bid_quantity,
            "ask_price": self.ask_price,
            "ask_quantity": self.ask_quantity
        }


@dataclass(slots=True)
class Candle:
    timestamp: float # Unix timestamp (ms o s)
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool # Flag para saber si es inmutable
    volatility: Optional[float] = field(default=None)
    reservation_price_neutral: Optional[float] = field(default=None)

    def __lt__(self, other):
        if not isinstance(other, Candle):
            return NotImplemented
        return self.timestamp < other.timestamp

    def __sub__(self, other):
        if not isinstance(other, Candle):
            return NotImplemented
        return self.close - other.close