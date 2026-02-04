import asyncio
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
                 repository: AsyncRepository,
                 redis_bus=None):  # Bus opcional para publicar trades
        
        self.symbol = symbol
        self.market_state = market_state
        self.engine = engine
        self.pm = portfolio_manager
        self.repository = repository
        self.redis_bus = redis_bus  # Para publicar trades via WebSocket

        self.rp_model = ReservePrice(symbol=symbol)
        
        # Variables para construir la vela de 1 segundo
        self.current_candle: Optional[Candle] = None
        self.last_second_processed = -1
        
        # Contador de velas procesadas para evitar trades en la primera vela
        self.candles_processed = 0



    async def on_tick(self, tick: Registro):
        """
        Esta función se llama CADA VEZ que llega un dato del Socket.
        """
        if tick.symbol != self.symbol: 
            return
        # 1. Mark-to-Market: Actualizamos el valor de la cartera en tiempo real
        self.engine.update_valuation({self.symbol: tick.bid_price}, tick.time)

        # 2. Lógica de Tiempo: ¿Hemos cambiado de segundo?
        timestamp_sec = tick.time
        second_idx = int(timestamp_sec) # Cada segundo es una vela nueva

            
        # --- CAMBIO DE SEGUNDO (CIERRE DE VELA) ---
        if self.last_second_processed != -1 and second_idx > self.last_second_processed:
            if self.current_candle:
                # A. Cerramos la vela
                self.current_candle.closed = True
                self.candles_processed += 1
                # Log solo cada 10 velas para no saturar
                if self.candles_processed % 10 == 0:
                    print(f"🕯️ {self.symbol}: Vela #{self.candles_processed} cerrada (O:{self.current_candle.open:.2f} C:{self.current_candle.close:.2f})")
                
                # B. Guardamos en memoria (MarketState) para indicadores
                self.market_state.add_candle(self.current_candle)
                
                # C. Guardamos en BBDD (Persistencia)
                asyncio.create_task(self.repository.save_candles(self.symbol, [self.current_candle]))
                
                # D. !!! EJECUTAMOS EL CEREBRO (solo después de warmup WebSocket) !!!
                # Requerimos mínimo 50 velas WebSocket para que las estrategias tengan datos suficientes
                WARMUP_CANDLES = 10
                if self.candles_processed >= WARMUP_CANDLES:
                    await self._run_strategy_cycle(tick)
                else:
                    # Mostrar progreso de warmup
                    remaining = WARMUP_CANDLES - self.candles_processed
                    if self.candles_processed == 1 or remaining % 10 == 0:
                        print(f"⏳ {self.symbol}: Warmup WebSocket {self.candles_processed}/{WARMUP_CANDLES} ({remaining} restantes)")

        # --- GESTIÓN DE LA VELA EN CURSO ---
        if second_idx > self.last_second_processed or self.last_second_processed == -1:
            # Empezamos nueva vela
            self.current_candle = Candle(
                timestamp=second_idx * 1000,  # Timestamp en ms
                open=tick.bid_price, high=tick.bid_price, low=tick.bid_price, close=tick.bid_price, 
                volume=0, closed=False
            )
            self.last_second_processed = second_idx
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
        
        # DEBUG: Ver qué señal devuelve la estrategia
        if self.candles_processed % 10 == 0:  # Cada 10 velas
            print(f"🔍 DEBUG {self.symbol}: signal={signal}, candles={self.candles_processed}")
        
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
        
        # Si el motor generó un trade nuevo, lo guardamos en SQL y publicamos
        current_history = self.engine.get_history_raw()
        if len(current_history) > prev_trades_len:
            new_trade = current_history[-1]
            print(f"🚀 TRADE EJECUTADO: {new_trade['side']} {self.symbol} @ {new_trade['price']}")
            await self.repository.save_trade(new_trade)
            
            if self.redis_bus:
                # Publicar evento de trade para actualización instantánea del frontend
                trade_event = {
                    "type": "TRADE",
                    "symbol": new_trade['symbol'],
                    "side": new_trade['side'],
                    "price": new_trade['price'],
                    "qty": new_trade['qty'],
                    "timestamp": new_trade['timestamp']
                }
                await self.redis_bus.publish(trade_event)
                
                # Guardar estado del engine en Redis para posiciones/PnL
                engine_state = self.engine.to_redis_state()
                await self.redis_bus.set_engine_state(self.symbol, engine_state)
                
                print(f"📡 Trade y estado publicados vía Redis: {new_trade['side']} {self.symbol}")
            else:
                print("⚠️ redis_bus no disponible, trade no publicado via WebSocket")