
CREATE TABLE IF NOT EXISTS market_data (
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    source_type VARCHAR(10) NOT NULL, -- 'SOCKET' o 'REST'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para velocidad
CREATE INDEX idx_symbol_time ON market_data(symbol, created_at DESC);