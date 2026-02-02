from sqlalchemy import Column, Float, String, BigInteger, Index, DateTime, Integer, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# Creamos la clase base de la que heredarán nuestros modelos
Base = declarative_base()

class TickSQL(Base):
    """
    Modelo que representa la tabla 'market_ticks' en PostgreSQL.
    Almacena tanto los datos crudos del mercado como los calculados por tu estrategia.
    """
    __tablename__ = 'market_ticks'

    # 1. Identificador único (BigInteger es mejor para tablas que crecen mucho)
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 2. Datos del Instrumento
    symbol = Column(String(20), nullable=False)  # Ej: "BTCUSDT"
    
    # 3. Tiempo
    # Guardamos el timestamp original del exchange (float/unix) para precisión
    exchange_time = Column(Float, nullable=False) 
    # Opcional: Tiempo de inserción en DB (útil para auditoría de latencia)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 4. Datos de Mercado (Order Book)
    # Usamos Float (Double Precision en Postgres) que mapea directo a float de Python
    bid_price = Column(Float, nullable=False)
    ask_price = Column(Float, nullable=False)
    bid_quantity = Column(Float, nullable=False)
    ask_quantity = Column(Float, nullable=False)

    # 5. Datos Calculados (Tu Estrategia)
    # Son 'nullable=True' porque al inicio del arranque no tengo la volatilidad calculada
    reservation_price = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)

    # 6. Índices de Rendimiento
    # Crea un índice compuesto. Esto lo hace instantáneo.
    __table_args__ = (
        Index('idx_symbol_time', 'symbol', 'exchange_time'),
    )

    def __repr__(self):
        return f"<TickSQL(symbol='{self.symbol}', price={self.reservation_price})>"

class CandleSQL(Base):
    """
    Modelo para almacenar velas (OHLCV) históricas o cerradas.
    Separado de los ticks para cálculos de estrategias (RSI, MA, etc.) más eficientes.
    """
    __tablename__ = 'candles'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    
    # Usamos BigInteger para timestamp en milisegundos (estándar en velas)
    # Es más eficiente para búsquedas de rangos que DateTime
    timestamp = Column(BigInteger, index=True, nullable=False) 
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Flag útil para saber si la vela es final o si (en un futuro) guardas snapshots parciales
    closed = Column(Boolean, default=True)
    volatility = Column(Float, nullable=True)
    reservation_price_neutral = Column(Float, nullable=True)

    # Índice compuesto para buscar rápidamente velas de un par en un rango de fecha
    __table_args__ = (
        Index('idx_candles_symbol_ts', 'symbol', 'timestamp'),
    )

    def __repr__(self):
        return f"<CandleSQL(symbol='{self.symbol}', time={self.timestamp}, close={self.close})>"


class TradeSQL(Base):
    """
    Registro histórico de ejecuciones (Trades).
    """
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(Float, nullable=False, index=True) # Unix timestamp
    
    side = Column(String(4), nullable=False) # "BUY" o "SELL"
    price = Column(Float, nullable=False)
    qty = Column(Float, nullable=False)
    total_usdt = Column(Float, nullable=False)
    
    # Métricas de calidad de ejecución (Opcionales pero recomendadas)
    edge_delta = Column(Float, nullable=True)
    q_optimal_theory = Column(Float, nullable=True)
    pnl_realized = Column(Float, nullable=True)

    def __repr__(self):
        return f"<TradeSQL({self.symbol}, {self.side}, {self.qty} @ {self.price})>"