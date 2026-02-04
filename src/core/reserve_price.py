import math
import asyncio
from typing import Dict
from src.core.models import Registro
from src.core.data_persister import DataPersister

#Clase que calcula el reservation price para cada symbol
class ReservePrice:
    def __init__(self, symbol:str, gamma = 0.5, lambda_ = 0.94):
        self.symbol = symbol
        self.gamma = gamma
        self.lambda_ = lambda_

        # Estado de la Volatilidad para el symbol
        self.variance = 0.0      # Varianza acumulada
        self.volatility = 0.0    # Sigma (Raíz de varianza)
        self.last_mid_price = None
        self.last_vol_update = 0 # Para controlar actualización cada 1s
        
        # Estado del Inventario (Simulado o real)
        self.inventory_q = 0.0
        self.last_printed_price = None   # q (Positivo=Largo, Negativo=Corto)

    def _calc_micro_price(self, tick: Registro) -> float:
        numerador = (tick.bid_quantity * tick.bid_price + tick.ask_quantity * tick.ask_price)
        denominador = (tick.bid_quantity + tick.ask_quantity)
        if denominador == 0:
            return (tick.bid_price + tick.ask_price) / 2
        return numerador / denominador
    
    def _calc_OBI(self, tick: Registro) -> float:
        diff = tick.bid_quantity - tick.ask_quantity
        total = tick.bid_quantity + tick.ask_quantity
        if total == 0: 
            return 0.0
        return diff / total

    def _update_volatility(self, current_mid: float, timestamp: float):
        if self.last_mid_price is None:
            self.last_mid_price = current_mid
            self.last_vol_update = timestamp
            return

        if timestamp - self.last_vol_update >= 1.0:
            #print(f"Actualizando volatilidad")
            # Retorno logarítmico
            log_ret = math.log(current_mid / self.last_mid_price)
            
            # Fórmula recursiva RiskMetrics
            self.variance = (1 - self.lambda_) * (log_ret**2) + \
                            (self.lambda_ * self.variance)
            
            self.volatility = math.sqrt(self.variance)
            
            # Actualizar estado
            self.last_mid_price = current_mid
            self.last_vol_update = timestamp

    def update_inventory_state(self, quantity: float):
        """
        Recibe la posición real del TraderEngine.
        q > 0: Estamos largos -> bajaremos el precio de compra para no acumular más riesgo.
        q < 0: Estamos cortos -> subiremos el precio para incentivar la compra.
        """
        self.inventory_q = quantity

    def _calc_reservation_price(self, tick: Registro) -> dict:
        """
        MÉTODO PRINCIPAL (HOT PATH)
        Se ejecuta cada vez que llega un mensaje del socket.
        """
        # 1. Calcular Mid Price Simple (Para Volatilidad)
        mid_price_simple = (tick.bid_price + tick.ask_price) / 2
        
        # 2. Actualizar Volatilidad (Internamente controla si toca o no)
        self._update_volatility(mid_price_simple, tick.time)
        
        # Si aún no tenemos volatilidad (arranque), usamos un default seguro o esperamos
        if self.volatility == 0:
            # Para depurar, podemos devolver valores parciales o None
            pass 

        # 3. Calcular Componentes de Precio
        micro_price = self._calc_micro_price(tick)
        theta = tick.ask_price - tick.bid_price
        obi = self._calc_OBI(tick)
        
        # 4. FÓRMULA MAESTRA DE AVELLANEDA + ALPHA
        # r = P_micro + theta * OBI - q * gamma * sigma^2
        
        inventory_risk_adj = self.inventory_q * self.gamma * (self.volatility ** 2)
        alpha_adj = theta * obi
        
        reservation_price = micro_price + alpha_adj - inventory_risk_adj
        
        
        return {
            "symbol": self.symbol,
            "reservation_price": reservation_price,
            "vol": self.volatility,

            # Datos originales del mercado (Necesarios para la base de datos)
            "time": tick.time,             # <--- Esto es lo que faltaba
            "bid_price": tick.bid_price,
            "ask_price": tick.ask_price,
            "bid_quantity": tick.bid_quantity,
            "ask_quantity": tick.ask_quantity,
            "inventory_q": self.inventory_q,
            "volatility": self.volatility     
        }
            
#Gestionar las múltiples instancias        
async def reserve_price(queue: asyncio.Queue, persister: DataPersister):
    print("🚀 Iniciando Motor de Precios Multi-Activo...")
    
    # DICCIONARIO DE ESTADO: Mapea "BTCUSDT" -> Objeto Calculadora BTC
    strategies: Dict[str, ReservePrice] = {}
    
    print(f"{'SYM':<8} | {'Reserva':<10} | {'Volatilidad':<10}")
    print("-" * 35)

    while True:
        tick: Registro = await queue.get()
        
        if tick.symbol is None:
            print("❌ Error: Recibido tick sin símbolo.")
            continue

        # Pattern: Lazy Initialization
        # Si es la primera vez que vemos esta moneda, creamos su cerebro
        if tick.symbol not in strategies:
            print(f"✨ Inicializando estrategia para {tick.symbol}")
            strategies[tick.symbol] = ReservePrice(tick.symbol)
        
        # Recuperamos el cerebro específico de esa moneda
        strategy = strategies[tick.symbol]
        
        # Ejecutamos cálculo
        result = strategy._calc_reservation_price(tick)

        await persister.add_metric(result)
        
        # Gestión de Logs (Para no saturar consola)
        # Solo imprimimos si el precio cambió respecto al último visto DE ESTA MONEDA
        current_r = round(result['reservation_price'], 2)
        if strategy.last_printed_price != current_r:
            print(f"{result['symbol']:<8} | {current_r:<10.2f} | {result['vol']:.6f}")
            strategy.last_printed_price = current_r

        queue.task_done()