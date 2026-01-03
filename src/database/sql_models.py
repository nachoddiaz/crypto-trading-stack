from sqlalchemy import Column, Float, String, BigInteger, Index, DateTime
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