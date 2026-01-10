import asyncio
from src.adapters.socket.binance_socket import BinanceDriver
from src.core import reserve_price as rp
from src.database.repository import AsyncRepository
from src.core.data_persister import DataPersister

async def main():
    #creo la tubería de datos
    cola = asyncio.Queue()
    exchange_name = "binance"
    target_symbols  = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT", "TRXUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "HYPEUSDT"]

    repo = AsyncRepository()
    persister = DataPersister(repo, batch_size=50, flush_interval=2)

    if exchange_name == "binance":
        #Asigno el driver y el simbolo
        driver = BinanceDriver(cola)
    else:
        raise ValueError("Exchange no soportado")

    await asyncio.gather(
        driver.backoff(target_symbols),
        #la conecto con el consumidor de precios
        rp.reserve_price(cola, persister),
        persister.worker()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Fin.")  