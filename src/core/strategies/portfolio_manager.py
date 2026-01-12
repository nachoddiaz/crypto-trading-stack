import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys

# Imports internos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.core.market_state import MarketState
from src.core.strategies.implementations import MACrossover, MomentumStrategy, EngulfingPattern

# Ruta al archivo generado por el optimizer.py
PARAMS_FILE = os.path.join(os.path.dirname(__file__), '../config/strategy_params.json')

class PortfolioManager:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        # Mapeo: "BTCUSDT" -> Lista de instancias de estrategias configuradas
        self.strategies_map: Dict[str, List] = {} 
        
        # Estado de asignación (Target Weights)
        # 0.0 = Fuera, 1.0 = Dentro (Simplificado para equiponderado)
        self.allocations = {s: 0.0 for s in symbols}
        
        # Cargar la configuración óptima al iniciar
        self._load_parameters()

    def _load_parameters(self):
        """
        Lee best_params.json y configura las estrategias.
        Si no existe el archivo, usa valores por defecto seguros.
        """
        config = {}
        if os.path.exists(PARAMS_FILE):
            try:
                with open(PARAMS_FILE, 'r') as f:
                    config = json.load(f)
                print(f"✅ PortfolioManager: Parámetros optimizados cargados desde {PARAMS_FILE}")
            except Exception as e:
                print(f"⚠️ Error leyendo params: {e}. Usando defaults.")
        else:
            print("⚠️ No se encontró strategy_params.json. Ejecuta optimizer.py primero.")

        for symbol in self.symbols:
            # Obtener configuración específica o defaults
            s_conf = config.get(symbol, {})
            
            # Parametrización dinámica
            ma_conf = s_conf.get("MA_CROSS", {"fast": 10, "slow": 50})
            mom_conf = s_conf.get("MOMENTUM", {"period": 14, "threshold": 0.001})
            pat_conf = s_conf.get("CANDLE_ENGULF", {}) # Engulfing no tiene params dinámicos en la clase base por ahora

            # Instanciamos las estrategias con los valores del JSON
            self.strategies_map[symbol] = [
                MACrossover(fast_period=ma_conf['fast'], slow_period=ma_conf['slow']),
                MomentumStrategy(period=mom_conf['period'], threshold=mom_conf['threshold']),
                EngulfingPattern() 
            ]

    def update_signals(self, symbol: str, state: MarketState) -> int:
        """
        HOT PATH: Ejecuta las estrategias sobre el estado actual del mercado.
        Retorna la señal consolidada (-1, 0, 1).
        """
        if symbol not in self.strategies_map:
            return 0

        # Obtener datos crudos de alta velocidad (Numpy)
        # Asegúrate de haber implementado get_ohlc_arrays en MarketState como vimos antes
        opens, highs, lows, closes = state.get_ohlc_arrays()
        
        if closes is None or len(closes) < 50: 
            return 0 # No hay suficientes datos para calcular

        final_vote = 0
        
        # Ejecutar cada estrategia (Numba inside)
        for strategy in self.strategies_map[symbol]:
            # Pasamos todos los arrays, la estrategia cogerá lo que necesite
            # Usamos kwargs para flexibilidad
            sig = strategy.calculate(closes=closes, opens=opens, highs=highs, lows=lows)
            
            # Sistema de Votación Simple
            final_vote += sig

        # Lógica de Consenso para Portfolio Equiponderado
        # Si la suma es positiva -> COMPRA/MANTENER
        # Si la suma es negativa -> VENTA
        # Si es 0 -> NEUTRAL (O mantener anterior, depende de tu perfil de riesgo)
        
        target_signal = 0
        if final_vote > 0: target_signal = 1
        elif final_vote < 0: target_signal = -1
        
        return target_signal

    def calculate_pnl_metrics(self, equity_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calcula las métricas de rendimiento exigidas en el PDF.
        Este método espera un DataFrame con índice Datetime y columna 'total_equity'.
        
        Retorna un diccionario listo para enviar a la API/Dashboard.
        """
        metrics = {
            "daily": 0.0,
            "monthly": 0.0,
            "qtd": 0.0,
            "ytd": 0.0,
            "total": 0.0
        }
        
        if equity_df.empty:
            return metrics

        # Asegurarse de que el índice es datetime y está ordenado
        if not isinstance(equity_df.index, pd.DatetimeIndex):
            try:
                equity_df.index = pd.to_datetime(equity_df.index)
            except:
                return metrics # Fallo en datos
        
        equity_df = equity_df.sort_index()
        
        current_equity = equity_df['total_equity'].iloc[-1]
        last_date = equity_df.index[-1]

        # Función auxiliar para calcular retorno desde una fecha
        def get_pct_change(start_date):
            # Buscar el índice más cercano usando 'asof' o searchsorted logic
            # Usamos truncate para filtrar rápido
            past_data = equity_df[equity_df.index <= start_date]
            if past_data.empty:
                # Si no hay datos tan antiguos, usamos el dato más antiguo disponible
                start_equity = equity_df['total_equity'].iloc[0]
            else:
                # Tomamos el último dato disponible antes o en la fecha de corte
                start_equity = past_data['total_equity'].iloc[-1]
            
            if start_equity == 0: return 0.0
            return (current_equity - start_equity) / start_equity

        # 1. Daily PnL (Desde el cierre de ayer o hace 24h)
        # Usamos 'normalize' para ir al inicio del día (00:00)
        start_today = last_date.normalize()
        # Si estamos en el mismo día, comparamos con el inicio del día. 
        # Si el dato más reciente es de ayer, el PnL diario es 0 o estático.
        metrics['daily'] = get_pct_change(start_today)

        # 2. Monthly PnL (Desde el día 1 del mes actual)
        start_month = last_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        metrics['monthly'] = get_pct_change(start_month)

        # 3. YTD PnL (Desde el 1 de Enero)
        start_year = last_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        metrics['ytd'] = get_pct_change(start_year)

        # 4. QTD PnL (Quarter to Date)
        # Meses de inicio de trimestre: 1, 4, 7, 10
        quarter_month = ((last_date.month - 1) // 3) * 3 + 1
        start_quarter = last_date.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        metrics['qtd'] = get_pct_change(start_quarter)

        # 5. Total PnL (Desde el inicio de los tiempos)
        initial_equity = equity_df['total_equity'].iloc[0]
        if initial_equity != 0:
            metrics['total'] = (current_equity - initial_equity) / initial_equity

        return metrics