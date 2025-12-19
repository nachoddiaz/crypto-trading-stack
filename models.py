from dataclasses import dataclass

@dataclass
class Registro:
    exchange: str
    symbol: str
    time: float
    bid_price: float
    bid_quantity: float
    ask_price: float
    ask_quantity: float
