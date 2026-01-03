import asyncio
from Socket_connection import BinanceDriver
import reserve_price as rp

async def main():
    #creo la tubería de datos
    cola = asyncio.Queue()
    exchange_name = "binance"
    target_symbols  = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT", "TRXUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "HYPEUSDT"]
    if exchange_name == "binance":
        #Asigno el driver y el simbolo
        driver = BinanceDriver(cola)
    else:
        raise ValueError("Exchange no soportado")

    await asyncio.gather(
        driver.backoff(target_symbols),
        #la conecto con el consumidor de precios
        rp.reserve_price(cola)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Fin.")  