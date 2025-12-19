import math
import asyncio
from dataclasses import dataclass
from typing import Optional
from models import Registro


class ReservePrice:
    def __init__(self, gamma = 0.5, lambda_ = 0.94,  ):
        self.gamma = gamma
        self.lambda_ = lambda_

        # Estado de la Volatilidad
        self.variance = 0.0      # Varianza acumulada
        self.volatility = 0.0    # Sigma (Raíz de varianza)
        self.last_mid_price = None
        self.last_vol_update = 0 # Para controlar actualización cada 1s
        
        # Estado del Inventario (Simulado o real)
        self.inventory_q = 0.0   # q (Positivo=Largo, Negativo=Corto)

    def _calc_micro_price(self, tick: Registro) -> float:
        numerador = (tick.bid_quantity * tick.bid_price + tick.ask_quantity * tick.ask_price)
        denominador = (tick.bid_quantity + tick.ask_quantity)
        if denominador == 0:
            return (tick.bid_price + tick.ask_price) / 2
        return numerador / denominador
    
    def _calc_OBI(self, tick: Registro) -> float:
        diff = tick.bid_quantity - tick.ask_quantity
        total = tick.bid_quantity + tick.ask_quantity
        if total == 0: return 0.0
        return diff / total

    def _update_volatility(self, current_mid: float, timestamp: float):
        if self.last_mid_price is None:
            self.last_mid_price = current_mid
            self.last_vol_update = timestamp
            return

        if timestamp - self.last_vol_update >= 1.0:
            print(f"Actualizando volatilidad")
            # Retorno logarítmico
            log_ret = math.log(current_mid / self.last_mid_price)
            
            # Fórmula recursiva RiskMetrics
            self.variance = (1 - self.lambda_) * (log_ret**2) + \
                            (self.lambda_ * self.variance)
            
            self.volatility = math.sqrt(self.variance)
            
            # Actualizar estado
            self.last_mid_price = current_mid
            self.last_vol_update = timestamp

    def _calc_reservation_price(self, tick: Registro) -> float:
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
        
        # 5. Calcular Spread
        half_spread = theta/2
        
        final_ask = reservation_price + half_spread
        final_bid = reservation_price - half_spread
        
        return {
            "r": reservation_price,
            "bid": final_bid,
            "ask": final_ask,
            "obi": obi,
            "vol": self.volatility
        }
            

        
async def reserve_price(queue: asyncio.Queue):
    print("🚀 Iniciando Motor de Precios...")
    pricer = ReservePrice()
    
    # Cabecera
    print(f"{'Precio de Reserva':<6} | {'BID':<10} | {'ASK':<10} | {'VOL':<10}")
    print("-" * 25)

    last_r = None

    while True:
        tick: Registro = await queue.get()
        
        resultado = pricer._calc_reservation_price(tick)
        
        if resultado:
             current_r = resultado['r']
             # Redondeamos a 2 decimales para la comparación (lo que se ve en pantalla)
             current_r_rounded = round(current_r, 2)
             
             # Solo imprimimos/guardamos si el precio reserva (visible) ha cambiado
             if last_r is None or current_r_rounded != last_r:
                 print(f"{current_r:.2f}      | {resultado['bid']:.2f} | {resultado['ask']:.2f} | {resultado['vol']:.5f}")
                 last_r = current_r_rounded
        else:
            # Si no hay resultado (ej: iniciando volatilidad), imprimimos status simple
            mid = (tick.bid_price + tick.ask_price) / 2
            print(f"Recibiendo datos... Mid: {mid:.2f} (Calculando Volatilidad)", end="\r")
