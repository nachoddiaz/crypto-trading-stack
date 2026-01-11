import asyncio
import websockets
import json
import time
from collections import defaultdict
from typing import Optional, List

# Imports internos
from src.interfaces.data_provider import ExchangeDrivers
from src.core.models import Registro


#Aseguro monotonizidad
class DataGuard:
    def __init__(self):
        self._last_state: Optional[Registro] = None
        self._dropped_duplicates = 0
        self._dropped_out_of_order = 0

    def monotonicity_duplicates(self, new_tick: Registro) -> bool:
        """
        Valido si el tick es nuevo y relevante.
        Retorna True si debes procesarlo, False si debes ignorarlo.
        Esperamos el dict crudo del socket de Binance bookTicker.
        """
        # CASO 1: Primer tick del sistema (Arranque)
        if self._last_state is None:
            self._last_state = new_tick
            return True

        # CASO 2: Validación de Monotonicidad (Tiempo)
        # Si el tick nuevo es más viejo o igual que el último procesado...
        if new_tick.time < self._last_state.time:
            self._dropped_out_of_order += 1
            # Log ligero (no imprimir siempre para no saturar consola)
            return False

        # CASO 3: Validación de Duplicados (Contenido)
        # Comparamos la tupla completa. Si precio Y volumen son idénticos...
        if (new_tick.bid_price == self._last_state.bid_price and
            new_tick.ask_price == self._last_state.ask_price and
            new_tick.bid_quantity == self._last_state.bid_quantity and
            new_tick.ask_quantity == self._last_state.ask_quantity):
            
            # Nota: Si solo cambia el timestamp pero los datos son iguales, es ruido.
            self._dropped_duplicates += 1
            # Actualizamos timestamp para mantener la monotonicidad, pero retornamos False
            # para no recalcular estrategias costosas.
            self._last_state.time = new_tick.time 
            return False

        # SI PASA TODOS LOS FILTROS:
        self._last_state = new_tick
        return True

    def get_stats(self):
        return {
            "duplicates_dropped": self._dropped_duplicates,
            "out_of_order_dropped": self._dropped_out_of_order
        }


class BinanceDriver(ExchangeDrivers):
    async def subscribe(self, symbols: list[str]):
        #con depth me traigo el libro de precios, usamos bookTicker para traer el precio de la orden
        streams = "/".join([f"{s.lower()}@bookTicker" for s in symbols])
        uri = f"wss://stream.binance.com:9443/stream?streams={streams}"
        print(f"Concenctando a Binance para {len(symbols)}: {symbols}")

        #Guardo el estado
        guards = defaultdict(DataGuard)



        async with websockets.connect(uri) as websocket:
            async for msg in websocket:
                raw_data = json.loads(msg)
                payload = raw_data.get('data')
                symbol = payload.get('s')
                normalized = self.normlize_message(payload, symbol)
                if normalized and guards[symbol].monotonicity_duplicates(normalized):
                    await self.queue.put(normalized.to_dict())
            raise websockets.ConnectionClosed(None, None)        
        
    #Normalizo el mensaje símbolo por símbolo
    def normlize_message(self, data: dict, symbol: str) -> Optional[Registro]:
        try:
            bid_price = float(data["b"])
            bid_quantity = float(data["B"])
            ask_price = float(data["a"])
            ask_quantity = float(data["A"])
            return Registro(
                exchange="Binance",
                symbol=symbol,
                time=time.time(),
                bid_price=bid_price,
                bid_quantity=bid_quantity,
                ask_price=ask_price,
                ask_quantity=ask_quantity,
            )
        except Exception as e:
            print(f"Error al normalizar el mensaje: {e}")
            return None
