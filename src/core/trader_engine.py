import math
from typing import Dict, List, Any, Optional

class TraderEngine:
    """
    Motor de ejecución de Paper Trading con Sizing basado en Volatilidad y Volumen.
    
    Responsabilidad Única (SRP):
    Gestionar inventario, aplicar restricciones temporales (1 min) y optimizar 
    el tamaño de la orden (Q*) según la volatilidad y liquidez del activo.
    """
    __slots__ = [
        'usdt_balance', 'crypto_balances', '_trades_history', '_equity_curve',
        'fee_rate', 'risk_budget', 'max_order_value', 'last_trade_ts'
    ]

    def __init__(self, initial_usdt: float = 10000.0, risk_budget_usdt: float = 100.0):
        # --- Estado ---
        self.usdt_balance = initial_usdt
        self.crypto_balances: Dict[str, float] = {} 
        
        # --- Control Temporal (Restricción 1 minuto) ---
        # Map: Symbol -> Timestamp del último trade
        self.last_trade_ts: Dict[str, float] = {}

        # --- Ledger ---
        self._trades_history: List[Dict[str, Any]] = []
        self._equity_curve: List[Dict[str, Any]] = [] 
        
        # --- Parámetros de Modelo ---
        self.fee_rate = 0.001        # Fee fija (ej. 0.1%)
        self.risk_budget = risk_budget_usdt # Presupuesto de riesgo por trade (base)
        
        # Hard cap de seguridad (ej. no más del 10% de la cuenta en un solo trade)
        self.max_order_value = 0.10 * self.usdt_balance 

    def get_position_size(self, symbol: str) -> float:
        """Devuelve 'q' la cantidad del activo para el feedback loop del Reserve Price."""
        return self.crypto_balances.get(symbol, 0.0)

    def _calculate_optimal_size(self, market_price: float, reserve_price: float, 
                                volatility: float, volume: float) -> float:
        """
        Calcula Q* basado en Risk Budget y Liquidez.
        
        Fórmulas:
          denom = Pmkt * sigma
          edge  = |rp - Pmkt| / denom
          base  = RiskBudget / denom
          Q_raw = base * edge
          Q* = min(Q_raw, 0.10 * VolumenTotal)
        """
        # Protecciones matemáticas
        if volatility <= 1e-9 or market_price <= 1e-9:
            return 0.0
        
        # 1. Cálculo de términos comunes
        denom = market_price * volatility
        
        # 2. Cálculo de Edge (Adimensional: Desviación estandarizada del precio)
        # edge = | rp - Pmkt | / (Pmkt * sigma)
        price_diff = abs(reserve_price - market_price)
        edge = price_diff / denom
        
        # 3. Cálculo de Base (Unidades de activo)
        # base = RiskBudget / (Pmkt * sigma)
        base = self.risk_budget / denom
        
        # 4. Tamaño crudo
        q_raw = base * edge
        
        # 5. Límite de Liquidez (10% del volumen del minuto)
        vol_limit = 0.10 * volume
        
        # Q* final
        return min(q_raw, vol_limit)

    def execute_signal(self, symbol: str, signal: int, market_price: float, 
                       timestamp: float, reserve_price: float,
                       volatility: float, volume: float):
        """
        Orquesta la ejecución:
        1. Verifica restricción de tiempo (1 min).
        2. Calcula Q*.
        3. Ejecuta orden.
        """
        if signal == 0: return

        # --- 1. Restricción Temporal (1 trade por minuto por par) ---
        last_ts = self.last_trade_ts.get(symbol, 0.0)
        # Si han pasado menos de 60 segundos desde el último trade, ignoramos
        if (timestamp - last_ts) < 60.0:
            # Opcional: print(f"⏳ Throttling {symbol}: wait {60 - (timestamp - last_ts):.1f}s")
            return

        # --- 2. Calcular Tamaño Óptimo (Q*) ---
        q_optimal = self._calculate_optimal_size(market_price, reserve_price, volatility, volume)
        
        if q_optimal <= 0: return

        # --- 3. Ejecución y Ajuste de Inventario ---
        if symbol not in self.crypto_balances:
            self.crypto_balances[symbol] = 0.0
        
        current_q = self.crypto_balances[symbol]
        trade_executed = False
        final_qty = 0.0
        pnl_impact = 0.0 # Cost or Revenue

        # --- COMPRA (Long) ---
        if signal == 1:
            # Verificar si tenemos edge positivo (rp > Pmkt para comprar barato)
            # Nota: Tu fórmula de edge usa valor absoluto, así que asumimos que la señal
            # externa ya valida la dirección (Buy si Pmkt < rp).
            
            # Límite de Capital Real: No gastar más de lo que tenemos
            max_buyable_qty = (self.usdt_balance / market_price) * (1 - self.fee_rate)
            
            # El tamaño es el mínimo entre: Modelo Matemático vs Capital Disponible
            qty_to_buy = min(q_optimal, max_buyable_qty)
            
            cost_usdt = qty_to_buy * market_price
            
            # Chequeo de seguridad (Max Order Value)
            if cost_usdt <= self.max_order_value and cost_usdt > 0:
                self.crypto_balances[symbol] += qty_to_buy
                self.usdt_balance -= cost_usdt
                
                trade_executed = True
                final_qty = qty_to_buy
                pnl_impact = -cost_usdt # Salida de caja
                print(f"🟢 BUY {symbol}: Q*={qty_to_buy:.4f} | VolLimit={0.1*volume:.2f} | EdgeRaw={abs(reserve_price-market_price)/market_price:.4%}")

        # --- VENTA (Short/Exit) ---
        elif signal == -1:
            # Límite de Inventario: No vender más de lo que tenemos (Spot)
            qty_to_sell = min(q_optimal, current_q)
            
            revenue_usdt = qty_to_sell * market_price * (1 - self.fee_rate)
            
            # Chequeo de seguridad (Max Order Value - opcional en venta, pero consistente)
            # Para ventas, solemos querer salir sí o sí, pero respetamos Q*
            if qty_to_sell > 0:
                self.crypto_balances[symbol] -= qty_to_sell
                self.usdt_balance += revenue_usdt
                
                trade_executed = True
                final_qty = qty_to_sell
                pnl_impact = revenue_usdt # Entrada de caja
                print(f"🔴 SELL {symbol}: Q*={qty_to_sell:.4f} | VolLimit={0.1*volume:.2f}")

        # --- 4. Registro y Actualización Temporal ---
        if trade_executed:
            # Actualizamos el timestamp del último trade para bloquear el siguiente minuto
            self.last_trade_ts[symbol] = timestamp
            
            self._log_trade(timestamp, symbol, "BUY" if signal == 1 else "SELL", 
                           market_price, final_qty, abs(pnl_impact), q_optimal)

    def update_valuation(self, current_prices: Dict[str, float], timestamp: float) -> float:
        """Mark-to-Market puro."""
        crypto_val = 0.0
        for sym, qty in self.crypto_balances.items():
            if qty > 0:
                crypto_val += qty * current_prices.get(sym, 0.0)
        
        total_equity = self.usdt_balance + crypto_val
        
        self._equity_curve.append({
            "timestamp": timestamp,
            "total_equity": total_equity,
            "usdt_balance": self.usdt_balance,
            "crypto_val": crypto_val
        })
        return total_equity

    def _log_trade(self, ts, sym, side, px, qty, total, q_opt):
        self._trades_history.append({
            "timestamp": ts,
            "symbol": sym,
            "side": side,
            "price": px,
            "qty": qty,
            "total_usdt": total,
            "q_optimal_theory": q_opt
        })

    # Getters
    def get_history_raw(self) -> List[Dict]: return self._trades_history
    def get_equity_curve_raw(self) -> List[Dict]: return self._equity_curve