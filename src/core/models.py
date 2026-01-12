from dataclasses import dataclass

@dataclass
class Registro:
    # Usamos __slots__ para reducir memoria y acelerar acceso (Golden Rule)
    __slots__ = ['exchange', 'symbol', 'time', 'bid_price', 'bid_quantity', 'ask_price', 'ask_quantity']
    
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


@dataclass
class Candle:
    __slots__ = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'closed']
    
    timestamp: float # Unix timestamp (ms o s)
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool # Flag para saber si es inmutable

    def __lt__(self, other):
        if not isinstance(other, Candle):
            return NotImplemented
        return self.timestamp < other.timestamp

    def __sub__(self, other):
        if not isinstance(other, Candle):
            return NotImplemented
        return self.close - other.close