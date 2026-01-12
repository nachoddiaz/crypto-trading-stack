import sys
import os
import time
import random
import numpy as np
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE IMPORTS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models import Candle, Registro
from src.core.market_state import MarketState
from src.core.trader_engine import TraderEngine
from src.middleware.dashboard_reporter import PortfolioReporter

# --- MOCK STRATEGY ---
class MockStrategy:
    def calculate(self, current_price: float, ma_fast: float) -> int:
        # Umbrales más sensibles para asegurar disparo en el test
        if current_price < ma_fast * 0.9995: return 1  # BUY (Cae un poquito)
        if current_price > ma_fast * 1.0005: return -1 # SELL (Sube un poquito)
        return 0

# --- DATA GENERATORS ---
def generate_historical_candles(n=100, start_price=50000.0) -> list[Candle]:
    candles = []
    price = start_price
    start_ts = time.time() - (n * 60)
    for i in range(n):
        change = np.random.normal(0, 10)
        price += change
        c = Candle(
            timestamp=start_ts + (i * 60),
            open=price, high=price+5, low=price-5, close=price,
            volume=1000.0, closed=True
        )
        candles.append(c)
    return candles

def generate_tick_from_price(price, timestamp) -> Registro:
    spread = 1.0
    return Registro(
        exchange="binance",
        symbol="BTCUSDT",
        time=timestamp,
        bid_price=price - (spread/2), # Precio al que vendes
        ask_price=price + (spread/2), # Precio al que compras
        bid_quantity=5.0,
        ask_quantity=5.0
    )

# --- INTEGRATION TEST ---
class SystemIntegrationTest:
    def __init__(self):
        print("🔧 Inicializando Sistema Completo...")
        self.symbol = "BTCUSDT"
        self.market_state = MarketState(window_size=1000)
        
        # RiskBudget alto para que el Q* no sea minúsculo
        self.engine = TraderEngine(initial_usdt=1000000.0, risk_budget_usdt=20.0)
        self.strategy = MockStrategy()
        
    def run_cold_path(self):
        print("\n🥶 [FASE 1] COLD PATH: Carga Histórica")
        history = generate_historical_candles(n=100, start_price=50000.0)
        self.market_state.initialize_history(history)
        return history[-1].close

    def run_hot_path(self, start_price):
        print("\n🔥 [FASE 2] HOT PATH: Tiempo Real")
        print(f"{'TIME':<4} | {'PRICE':<8} | {'SIGNAL':<6} | {'R_PRICE':<8} | {'EDGE':<6} | {'ACCIÓN ENGINE':<30} | {'USDT':<10} | {'BTC':<8}")
        print("-" * 125)

        current_price = start_price
        
        # Simulamos 120 segundos
        for i in range(1, 121):
            ts = time.time() + i
            
            # 1. Movimiento de Precio Controlado
            # Tick 10-20: Bajada fuerte -> Debería dar BUY
            if 10 < i < 20: current_price *= 0.9995
            # Tick 60-70: Subida fuerte -> Debería dar SELL
            elif 60 < i < 70: current_price *= 1.0005
            else: current_price += np.random.normal(0, 2)

            tick = generate_tick_from_price(current_price, ts)
            self.market_state.on_tick(tick)
            
            # 2. Estrategia
            closes = self.market_state.get_arrays()
            if len(closes) < 10: continue
            ma_fast = np.mean(closes[-10:])
            signal = self.strategy.calculate(current_price, ma_fast)
            
            # 3. GESTIÓN DE RIESGO (SIMULACIÓN DE EDGE)
            # AQUÍ ESTÁ EL TRUCO: Si hay señal, inyectamos "Alpha" en el Reserve Price
            # para que el Engine vea beneficio matemático y opere.
            
            reserve_price = current_price # Default: Sin opinión (Edge = 0)
            
            if signal == 1:
                # Si quiero comprar, mi modelo dice que esto vale MÁS (ej. +0.3%)
                # Market: 50,000 | Reserve: 50,150 -> Edge positivo -> COMPRA
                reserve_price = current_price * 1.02
            elif signal == -1:
                # Si quiero vender, mi modelo dice que esto vale MENOS (ej. -0.3%)
                # Market: 50,000 | Reserve: 49,850 -> Edge positivo -> VENTA
                reserve_price = current_price * 0.98

            # 4. Ejecución
            prev_hist_len = len(self.engine.get_history_raw())
            
            # Usamos ask_price para comprar, bid_price para vender
            exec_price = tick.ask_price if signal == 1 else tick.bid_price
            
            self.engine.execute_signal(
                symbol=self.symbol,
                signal=signal,
                market_price=exec_price,
                timestamp=ts,
                reserve_price=reserve_price, # Pasamos el precio con Alpha
                volatility=0.005, # Volatilidad fija para test
                volume=5000.0     # Volumen alto para no limitar por liquidez
            )
            
            self.engine.update_valuation({self.symbol: current_price}, ts)

            # 5. Logs (Solo eventos relevantes)
            if signal != 0:
                did_trade = len(self.engine.get_history_raw()) > prev_hist_len
                
                # Calculamos el edge que vio el engine para mostrarlo
                fee_cost = exec_price * self.engine.fee_rate
                edge_view = abs(reserve_price - exec_price) - fee_cost
                
                action_txt = "🛑 Throttled/Low Edge"
                if did_trade:
                    last = self.engine.get_history_raw()[-1]
                    action_txt = f"✅ {last['side']} {last['qty']:.4f}"
                
                # Solo imprimimos si hay señal para no saturar
                pos = self.engine.get_position_size(self.symbol)
                print(f"T+{i:<3} | {current_price:<8.2f} | {signal:<6} | {reserve_price:<8.2f} | {edge_view:<6.2f} | {action_txt:<30} | {self.engine.usdt_balance:<10.1f} | {pos:<8.4f}")

    def generate_report(self):
        print("\n📊 [FASE 3] REPORTING")
        raw_trades = self.engine.get_history_raw()
        if not raw_trades:
            print("⚠️ No se realizaron trades.")
            return

        df = PortfolioReporter.create_trades_df(raw_trades)
        # Usamos las claves correctas que definimos en trader_engine.py
        cols = ['timestamp', 'side', 'price', 'qty', 'edge_delta', 'q_optimal_theory']
        print(df[cols].to_string(index=False))

        final_equity = self.engine.get_equity_curve_raw()[-1]['total_equity']
        print(f"\n💰 Equity Final: {final_equity:.2f} USDT")

if __name__ == "__main__":
    test = SystemIntegrationTest()
    last = test.run_cold_path()
    test.run_hot_path(last)
    test.generate_report()