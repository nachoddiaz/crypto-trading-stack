import asyncio
import time
from typing import Optional

# Imports de tus módulos
from src.core.models import Registro, Candle
from src.core.market_state import MarketState
from src.core.trader_engine import TraderEngine
from src.core.strategies.portfolio_manager import PortfolioManager
from src.database.repository import AsyncRepository
from src.core.reserve_price import ReservePrice

class RealTimeProcessor:
    def __init__(self, 
                 symbol: str, 
                 market_state: MarketState, 
                 engine: TraderEngine, 
                 portfolio_manager: PortfolioManager,
                 repository: AsyncRepository):
        
        self.symbol = symbol
        self.market_state = market_state
        self.engine = engine
        self.pm = portfolio_manager
        self.repository = repository

        self.rp_model = ReservePrice(symbol=symbol)
        
        # Variables para construir la vela de 1 minuto
        self.current_candle: Optional[Candle] = None
        self.last_minute_processed = -1



    async def on_tick(self, tick: Registro):
        """
        Esta función se llama CADA VEZ que llega un dato del Socket.
        """
        if tick.symbol != self.symbol: return
        # 1. Mark-to-Market: Actualizamos el valor de la cartera en tiempo real
        self.engine.update_valuation({self.symbol: tick.bid_price}, tick.time)

        # 2. Lógica de Tiempo: ¿Hemos cambiado de minuto?
        timestamp_sec = tick.time
        minute_idx = int(timestamp_sec // 60) # Truco matemático para detectar el minuto

        if self.symbol == "BTCUSDT":
            import datetime
            # Convertir a hora legible para que TU lo entiendas
            hora_tick = datetime.datetime.fromtimestamp(timestamp_sec).strftime('%H:%M:%S')
            
        # --- CAMBIO DE MINUTO (CIERRE DE VELA) ---
        if self.last_minute_processed != -1 and minute_idx > self.last_minute_processed:
            if self.current_candle:
                # A. Cerramos la vela
                self.current_candle.closed = True
                print(f"🕯️ Cierre de Vela {self.symbol}: {self.current_candle.open} ,{self.current_candle.close}")
                
                # B. Guardamos en memoria (MarketState) para indicadores
                self.market_state.add_candle(self.current_candle)
                
                # C. Guardamos en BBDD (Persistencia)
                # (Lo lanzamos como tarea aparte para no bloquear)
                asyncio.create_task(self.repository.save_candles(self.symbol, [self.current_candle]))
                
                # D. !!! EJECUTAMOS EL CEREBRO !!!
                await self._run_strategy_cycle(tick)

        # --- GESTIÓN DE LA VELA EN CURSO ---
        if minute_idx > self.last_minute_processed or self.last_minute_processed == -1:
            # Empezamos nueva vela
            self.current_candle = Candle(
                timestamp=minute_idx * 60 * 1000, 
                open=tick.bid_price, high=tick.bid_price, low=tick.bid_price, close=tick.bid_price, 
                volume=0, closed=False
            )
            self.last_minute_processed = minute_idx
        else:
            # Actualizamos vela existente
            if self.current_candle:
                self.current_candle.high = max(self.current_candle.high, tick.bid_price)
                self.current_candle.low = min(self.current_candle.low, tick.bid_price)
                self.current_candle.close = tick.bid_price

    async def _run_strategy_cycle(self, tick):
        """
        El ciclo de decisión: Estrategia -> Riesgo -> Ejecución -> Guardado
        """
        # 1. Preguntamos al PortfolioManager qué hacer
        signal = self.pm.update_signals(self.symbol, self.market_state)
        
        if signal == 0:
            return # Nada que hacer

        # 2. Calcular Reservation Price usando el modelo Avellaneda-Stoikov
        # Actualizamos el inventario en el modelo antes de calcular
        q = self.engine.get_position_size(self.symbol)
        self.rp_model.update_inventory_state(q)
        
        # Calculamos reservation price con todos sus componentes
        rp_result = self.rp_model._calc_reservation_price(tick)
        reservation_price = rp_result['reservation_price']
        volatility = rp_result['volatility']

        # 3. EJECUCIÓN (Engine)
        # Guardamos cuántos trades había antes
        prev_trades_len = len(self.engine.get_history_raw())
        
        self.engine.execute_signal(
            symbol=self.symbol,
            signal=signal,
            market_price=tick.bid_price,
            timestamp=tick.time,
            reserve_price=reservation_price,
            volatility=volatility,
            volume=10000.0 # Volumen ficticio alto para asegurar liquidez en paper trading
        )
        
        # 4. PERSISTENCIA DEL TRADE
        # Si el motor generó un trade nuevo, lo guardamos en SQL
        current_history = self.engine.get_history_raw()
        if len(current_history) > prev_trades_len:
            new_trade = current_history[-1]
            print(f"🚀 TRADE EJECUTADO: {new_trade['side']} {self.symbol} @ {new_trade['price']}")
            await self.repository.save_trade(new_trade)