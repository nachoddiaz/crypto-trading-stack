import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Ajustar path para importar src
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.core.portfolio_manager import PortfolioManager
from src.core.market_state import MarketState
from src.core.models import Candle

# --- MOCKING: Simulamos el MarketState para no depender del WebSocket real ---
class MockMarketState(MarketState):
    def __init__(self):
        # Inicializamos sin llamar a super para control total
        self.closed_candles = []
        self.current_candle = None

    def load_synthetic_data(self, trend="bullish"):
        """Genera 100 velas sintéticas para forzar una señal"""
        print(f"🧪 Generando datos sintéticos ({trend})...")
        self.closed_candles = []
        
        price = 100.0
        
        for i in range(200):
            # Tendencia Alcista: Sube 0.5% cada vela
            if trend == "bullish":
                change = 1.005 
            # Tendencia Bajista: Baja 0.5% cada vela
            else:
                change = 0.995
                
            price = price * change
            
            # Crear Vela Falsa
            c = Candle(
                timestamp=time.time() * 1000 + (i * 60000),
                open=price * 0.99,
                high=price * 1.01,
                low=price * 0.98,
                close=price,
                volume=1000.0,
                closed=True
            )
            self.closed_candles.append(c)

    # El método que usará el PortfolioManager
    def get_ohlc_arrays(self):
        closes = np.array([c.close for c in self.closed_candles])
        opens = np.array([c.open for c in self.closed_candles])
        highs = np.array([c.high for c in self.closed_candles])
        lows = np.array([c.low for c in self.closed_candles])
        return opens, highs, lows, closes
import time

def test_integration():
    print("🚀 INICIANDO TEST DE INTEGRACIÓN DE ESTRATEGIAS\n")
    
    # 1. Configuración
    symbol = "BTCUSDT"
    manager = PortfolioManager([symbol])
    
    # 2. Test de Señal de COMPRA (Golden Cross + Momentum)
    print("--- Test 1: Generación de Señales (Hot Path) ---")
    mock_state = MockMarketState()
    mock_state.load_synthetic_data(trend="bullish")
    
    # Ejecutamos el manager
    signal = manager.update_signals(symbol, mock_state)
    
    print(f"📊 Señal calculada por Numba: {signal}")
    
    if signal == 1:
        print("✅ ÉXITO: El sistema detectó la tendencia alcista (BUY).")
    elif signal == 0:
        print("⚠️ AVISO: Señal Neutra. Puede que las medias sean muy lentas para 200 velas.")
    else:
        print("❌ FALLO: Señal de Venta en tendencia alcista.")

    # 3. Test de PnL (Cold Path)
    print("\n--- Test 2: Cálculo de Métricas PnL (Dashboard) ---")
    
    # Creamos una curva de capital ficticia:
    # Empieza en 10,000 el 1 de Enero
    # Termina en 11,000 hoy (10% de beneficio)
    dates = pd.date_range(start="2024-01-01", end=datetime.now(), freq="D")
    values = np.linspace(10000, 11000, len(dates))
    
    # Añadimos ruido para realismo
    equity_df = pd.DataFrame({"total_equity": values}, index=dates)
    
    # Ejecutamos cálculo
    metrics = manager.calculate_pnl_metrics(equity_df)
    
    print("📈 Métricas Calculadas:")
    for k, v in metrics.items():
        print(f"   - {k.upper()}: {v*100:.2f}%")
        
    # Validaciones básicas
    if metrics['total'] > 0.09 and metrics['total'] < 0.11:
         print("✅ ÉXITO: El PnL Total es correcto (~10%).")
    else:
         print(f"❌ FALLO: PnL Total esperado 10%, recibido {metrics['total']*100:.2f}%")

    if metrics['ytd'] != 0:
        print("✅ ÉXITO: YTD calculado correctamente.")

if __name__ == "__main__":
    test_integration()