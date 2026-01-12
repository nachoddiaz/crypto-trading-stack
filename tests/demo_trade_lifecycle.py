import sys
import os
import time
from datetime import datetime

# Ajusta el path para importar tus módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.trader_engine import TraderEngine
from src.middleware.dashboard_reporter import PortfolioReporter

# --- MOCKING / SIMULACIÓN DE DATOS ---
class MarketSimulator:
    def __init__(self):
        self.symbol = "BTCUSDT"
        # Escenario diseñado para testear los 3 casos: Normal, Throttling y Volume Limit
        self.ticks = [
            # T1: Inicialización
            {"time": 1700000000, "price": 50000.0, "reserve": 50000.0, "vol": 0.01, "volume": 100.0, "signal": 0, "desc": "Inicio"},
            
            # T2: [TEST FORMULA] Señal de COMPRA Estándar
            # Pmkt=50k, Sigma=0.01 -> Denom=500
            # RiskBudget=100 -> Base = 100/500 = 0.2
            # Diff=500 -> Edge = 500/500 = 1.0
            # Q_raw = 0.2 * 1.0 = 0.2 BTC
            # VolLimit = 10% de 100 = 10 BTC
            # ESPERADO: 0.2 BTC
            {"time": 1700000060, "price": 50000.0, "reserve": 50500.0, "vol": 0.01, "volume": 100.0, "signal": 1, "desc": "✅ Señal Válida (Risk Budget Pure)"},
            
            # T3: [TEST THROTTLING] Señal válida pero muy pronto (+30s)
            # El engine debería ignorarla porque no ha pasado 1 minuto
            {"time": 1700000090, "price": 50000.0, "reserve": 51000.0, "vol": 0.01, "volume": 100.0, "signal": 1, "desc": "⏳ Señal Throttled (< 1 min)"},
            
            # T4: [TEST VOLUMEN] Señal Válida tras espera (+70s desde la última aceptada)
            # Pmkt=50k, Sigma=0.01 -> Base=0.2
            # Diff=2000 -> Edge = 4.0
            # Q_raw = 0.2 * 4.0 = 0.8 BTC
            # Volumen=2.0 -> VolLimit = 10% de 2.0 = 0.2 BTC
            # ESPERADO: min(0.8, 0.2) = 0.2 BTC
            {"time": 1700000130, "price": 50000.0, "reserve": 48000.0, "vol": 0.01, "volume": 2.0, "signal": -1, "desc": "📉 Señal Volume Limited (Low Liquidity)"}
        ]
        self.current_idx = 0

    def get_next_tick(self):
        if self.current_idx >= len(self.ticks):
            return None
        tick = self.ticks[self.current_idx]
        self.current_idx += 1
        return tick

def calculate_manual_q_star(tick, risk_budget):
    """Cálculo 'en la sombra' para validar la lógica del Engine"""
    pmkt = tick['price']
    rp = tick['reserve']
    sigma = tick['vol']
    vol_total = tick['volume']
    
    if sigma <= 0 or pmkt <= 0: return 0.0
    
    # 1. Base y Edge
    denom = pmkt * sigma
    edge = abs(rp - pmkt) / denom
    base = risk_budget / denom
    
    q_raw = base * edge
    
    # 2. Límite Volumen
    vol_limit = 0.10 * vol_total
    
    return min(q_raw, vol_limit)

def run_simulation():
    RISK_BUDGET = 100.0 # 100 USDT de riesgo por trade
    
    print("⚙️  Inicializando TraderEngine (RiskBudget Mode)...")
    engine = TraderEngine(initial_usdt=100000.0, risk_budget_usdt=RISK_BUDGET) 
    
    sim = MarketSimulator()
    
    # --- CABECERA ACTUALIZADA CON BALANCES ---
    print(f"{'TIME':<8} | {'PRICE':<8} | {'Q* (Manual)':<12} | {'ACCIÓN ENGINE':<40} | {'USDT':<12} | {'BTC':<10} | {'RESULTADO'}")
    print("-" * 135)

    last_trade_time = 0

    while True:
        tick = sim.get_next_tick()
        if not tick: break
        
        signal = tick["signal"]
        ts = tick["time"]
        
        # --- Validación Manual (Shadow Testing) ---
        q_manual = 0.0
        validation_note = ""
        
        if signal != 0:
            # 1. Chequeo de tiempo manual
            if (ts - last_trade_time) < 60 and last_trade_time != 0:
                validation_note = "[ESPERADO: SKIP por Tiempo]"
                q_manual = 0.0
            else:
                # 2. Cálculo matemático manual
                q_manual = calculate_manual_q_star(tick, RISK_BUDGET)
                validation_note = f"[ESPERADO: {q_manual:.4f}]"

        # --- Ejecución Real ---
        len_history_pre = len(engine.get_history_raw())
        
        engine.execute_signal(
            symbol=sim.symbol,
            signal=signal,
            market_price=tick["price"],
            timestamp=ts,
            reserve_price=tick["reserve"],
            volatility=tick["vol"],
            volume=tick["volume"]
        )
        
        # Verificamos si operó
        history = engine.get_history_raw()
        did_trade = len(history) > len_history_pre
        
        engine_action = tick['desc']
        if did_trade:
            last_trade = history[-1]
            q_executed = last_trade['qty']
            engine_action += f" -> ✅ EJECUTADO: {q_executed:.4f}"
            last_trade_time = ts # Actualizamos nuestro tracker manual
            
            # Validación Final
            if abs(q_executed - q_manual) < 1e-5:
                res_icon = "✅ OK"
            else:
                res_icon = f"❌ ERROR (Exp: {q_manual})"
        else:
            if signal != 0:
                engine_action += " -> 🛑 IGNORADO/THROTTLED"
                res_icon = "✅ OK" if q_manual == 0 else "❌ ERROR (Debió operar)"
            else:
                res_icon = "-"

        # --- OBTENER BALANCES PARA DISPLAY ---
        current_usdt = engine.usdt_balance
        current_btc = engine.get_position_size(sim.symbol)

        # --- Log Visual ---
        q_str = f"{q_manual:.4f}" if q_manual > 0 else "-"
        # Se añaden las columnas de balances al print
        print(f"T+{ts % 1000:<4} | {tick['price']:<8} | {q_str:<12} | {engine_action:<40} | {current_usdt:<12.2f} | {current_btc:<10.4f} | {res_icon} {validation_note}")
        
        engine.update_valuation({sim.symbol: tick['price']}, ts)
        time.sleep(0.2)

    # Reporte
    print("\n🏁 Test Finalizado.")
    df = PortfolioReporter.create_trades_df(engine.get_history_raw())
    if not df.empty:
        print("\nResumen de Operaciones:")
        print(df[['timestamp', 'side', 'qty', 'price', 'q_optimal_theory']].to_string(index=False))

if __name__ == "__main__":
    run_simulation()