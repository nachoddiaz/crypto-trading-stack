En primer lugar creo la estructura del proyecto
Creación del entorno virtual
Creación del directorio Justificaciones_Uso donde explicaré los pros y contras de cada tecnología así como la decisión tomada
Creacion del directorio Testeo_Strats donde explicaré el proceso de elección de los parámetros para las estrategias


Creación un script de prueba con el que testear el mejor almacenamiento para implementar la conexión socket
    
    Instalación de las librerías necesarias
       instalo websockets (conexion socket con Binance)
       asyncio (Eventos asíncronos)
       json (Codificación de datos devueltos) -> ya viene con Python
       time (medir tiempos de almacenamiento) -> ya viene con Python
       aiofiles (para poder escribir en archivos de forma asíncrona)
        
    Error: Llamé al fichero socket.py cuando ya existe una libreria con el mismo nombre   
    Pregunta: cálculo del precio al que se abre la orden
    Respuesta: ¿precio de fill?
            ¿impacto orden según cantidad y raiz cuadrada?
            con impacto limitado, modelizar probabilidad de fill
            Usar top of the book -> Lowest Ask al comrar y Highest Bid al vender
            Asumir cero impacto -> precio de fill = precio del top of the book y no modifico precio de fill

    Cambio @depth por @bookTicker al conectar el socket y me quedo con el precio medio
    Error: precios vienen formato string, debo cambiarlo a float para operar con ellos
    Pregunta: Uso de mid price
    Respuesta: uso de mid-price modificado a través de la contrucción de un reservation o indiference price (según Avellanda-Stoikov) (https://people.orie.cornell.edu/sfs33/LimitOrderBook.pdf)
    el mid-price modificado es la valoración subjetiva ajustada al riesgo del trader, que se utiliza para centrar las cotizaciones (skewing quotes) y gestionar el inventario hacia cero.
    Fórmula simplificada: reservation_price = micro_price + theta * OBI - q * gamma *sigma^2
    Donde:
    reservation_price = precio reserva
    micro_price = precio medio
    theta = cambio a dólares de la presión en el order book
    OBI = Order Book Imbalance
    q = quantity
    gamma = Aversión al riesgo (cte) penaliza tener inventario. Función de utilidad -exp(-gamma * inventario)
    sigma = Volatilidad

    Para calcular la volatilidad necesito valores en t-x donde x indica la ventana temporal de la volatilidad
    
    
    Pregunta: definición de ingestion time
    Respuesta: tiempo desde publicación del mensaje hasta poder ser procesado

    Pregunta: cómo calculo la volatilidad?
    Respuesta: comprobar si es consistente el cálculo de la volatilidad mediante vol de best ask y best bid
        mid price modificado = mid price + theta * OBI  -q * gamma * vol^2 
    Pregunta: necesario tener dos sockets, bookTicker para calcular el precio mid y aggTrade con el que calcular la volatilidad realizada?
    Respuesta: Únicamente con bookTicker (Q_ask, P_ask, Q_bid, P_bid), cálculo micro pice (Q_bid * P_bid + Q_ask * P_ask) / (Q_bid + Q_ask), calculo volatilidad = (1-lambda) * log_return + lambda* vol_t-1. Precio_reserva = P_micro - (q * gamma * vol^2). 
    Cálculo del spread = 
    Decisión: lambda = 0.94 para datos diarios popularizado por JPMorgan
    Decisión: gamma = 0.5
    Decisión: theta = Spread promedio / 2

    Decisión: para guardar los datos del socket utilizo Dataclasses ya que ocupa menos memoria que un diccionario, lo guardo en un script aparte
    Decisión: Creo clase abstracta para poder soportar diferentes exchanges via Interfaz -> Adaptador
    Decisión: Separo el cálculo del precio reserva en otra función para modularizar el código
    Decisión: El proceso de webcokets, calculo micropice, calculo vol EWMA, calculo reservation price lo hago en el mismo script para eliminar latencia interna.

    Decisión: en sockets_Binance.py implemento la lectura del socket, backoff, check de monotonicidad, normalización de datos para soportar diferentes exchanges y review de duplicidad

---------------------------------------------------------------------------------------------------------------------------------------------------------
Decisión de almacenamiento: Genero datos con la misma estructura que el socket para poder compararlos y ver el impacto de cada almacenamiento

Instalación de pandas pymongo psycopg2-binary pyarrow fastparquet sqlalchemy
Creo el script data_generator.py con el que creo un json con la misma estructura que el socket
Guardo la información en los 5 métodos de almacenamiento
Creo el script benchmark_runner.py con el que realizo las comparativas de velocidad de escritura y tamaño de fichero
No tengo Docker, ni postgresql ni mongoDB.
    1. Instalo postgresql con TimescaleDB ya que permite consultas SQL estándar pero con velocidad de ingestión masiva
        1.1 Instalo Docker
        1.2 Creo el archivo de infraestructura docker-compose.yml
            a. Descargo TimescaleDB (que incluye Postgres)
            b. Abro el puerto 5432
            c. Guardo los datos en una carpeta local llamada timescale_data para que no se borren si apagas el PC
        1.3 Arranco el contenedor con el comando "docker-compose up -d"
        Error: Permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
        Solución: agregar usuario a docker group con sudo usermod -aG docker $USER

    2. Instalo MongoDB
        2.1 Actualizo docker-compose.yml con la información de mongo
        2.2 Vuelvo a levantar el contenedor con el comando "docker-compose up -d"

Ahora puedo ejecutar benchmark_runner.py con todas las alternativas
CSV, SQLite y Parquet escriben directamente en el disco duro lo que las convierte en las opciones más rápidas, pero tienen un fallo que las elimina, al escribir directamente en el disco duro del equipo, tiene capacidad más limitada, imposibilidad de replicación de datos y por lo tanto no es escalable.
MongoDB tiene estructura servidor-cliente y una velicidad decente, pero no fuerza sincronización de datos permitiendo errores
PostgreSQL tienen una velocidad suficiente (5000 ticks/s mientras Binance en tráfico pico nos envía hasta 1000 ticks/s), tiene estructura cleinte-servidor permitiendo una mayor seguridad y escalabilidad, fuerza sincronización de datos evitando errores
Decisión: se selecciona PostgreSQL

----------------------------------------------------------------------------------------------------------------------------------
Una vez seleccionado el almacenamiento, proceod a implementar el socket con el resto de criptos modularizando el código
Error: crear interfaz y adaptador para cada cripto ya que cada cripto crearía su propio socket, aumenta la complejidad en O(n)
Solución: el driver del exchange seleccionado maneja la conexión pero la interfaz debe soportar una lista, no sólo un símbolo
    1.1: URL multiplexada para recibir múltiples criptos
    1.2: la url de @bookTicker debe cambiar de "wss://stream.binance.com:9443/ws/{symbol.lower()}@bookTicker" a "wss://stream.binance.com:9443/stream?streams=CRIPTO1@bookTicker,CRIPTO2@bookTicker..."

Problema: para implantar monotonicidad y no duplicidad necesito aplcar esta clase a cada par
Solución: creo un diccionario inteligente con "defaultdict" para on crear uno por uno para cada par

Debo cambiar la función de normalización para que soporte el diccionario con todos los pares de cripto. Además, debo cambiar mi dataclass "registro" para que soporte el campo "símbolo".
Por otro lado, debo cambiar la clase que calcula el precio de reserva para que soporte el diccionario con todos los pares de cripto.


----------------------------------------------------------------------------------------------------------------------------------

Al ir metiendo más funcionalidades (ingesta de datos via rest y socket + reserva de precio + almacenamiento en bbdd) necesito una arquitectura más modular que escale mejor, itnento impleemntar arquitectura hexagonal con puertos (interfaces) y adaptadores (implementación concreta)

----------------------------------------------------------------------------------------------------------------------------------

Al cambiar el nombre del proyecto para realizar la entrega, debo cambiar también el nombre del entorno virtual, para ellos ejecuto rm -rf .venv y uv sync que sincroniza el entorno virtual con el archivo uv.lock


----------------------------------------------------------------------------------------------------------------------------------

Almacenamiento de los datos ingestados por el socket, necesito SQLAlchemy para poder decirle a python como traducir los objetos descargados a filas en la base de datos PostgreSql
Instalo asyncpg
En el archivo sql_models.py defino la estructura de la tabla
En el archivo repository.py gestiono la conexión, creo las tablas si no existen, creo una lista de diccionarios (del buffer) y los inserto, además una función auxiuliar para testear correctamente la conexión.
En "test_db_connection.py" realizo pruebas para verificar que la conexión a la base de datos es correcta, para ello una vez creado el script, levanto mi servidor docker con "docker run --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=trading_db -p 5432:5432 -d postgres:13"

Ahora realizo la prueba con datos que vienen del socket.
Para hacerlo, implemento un buffer como solución, el cual recibe los paquetes del socket y los inserta en la base de datos en segundo plano.
Guardo datos cada 50ticks o cada 2 segndos
Para poder visualizar los datos almacenados dentro de la propia base de datos, uso la extensión SQLTools


----------------------------------------------------------------------------------------------------------------------------------

Tengo problemas de escalabilidad al tener una arquitectura monolítica asíncrona ya que mi proceso asíncrono (asyncio.Queue) vive en la RAM, por lo tanto necesito implementar una arquitectura microservicios, pese a aumentar un poco la latencia, mi programa será persistente (Ej: resistente ante bloqueos en recepción de datos) y más escalable.
No uso Kafka por su complejidad, mantenimiento y sobre todo porque con este orden de mágintud de símbolos (10) no es necesario.
El punto medio es usar Redis Stream con lo que varios consumidores puedan leer el mismo dato (estrategia y dashboard)
Instalo redis y msgpack porque quiero conversiones JSON rápidas.
Para no alterar la lógica del socket, creo una clase RedisBus que también tenga un método .put(), pero que por dentro serialice con msgpack y lo envíe a Redis.
Modifico la función data_persister porque ya lo gestiona Redis.
Ahora mi código fuciona tal que: 
    1. ingestor.py Baja datos y los empuja a Redis
    2. Redis es la tubería e datos
    3. persister.py recibe datos de Redis y los pasa a la lógica
    4. data_persister.py recibe datos de la lógica y los inserta en la base de datos

----------------------------------------------------------------------------------------------------------------------------------

**Ingesta de datos via RESTAPI**

Utilizando /api/v3/klines obtenemos los valores OHLCV para cada símbolo en el intervalo de timepo indicado (tíene limite de 1000 velas por petición)

Añado la librería request

Debo separar el histórical buffer de la vela actual por lo tanto dentro de mi script models.py creo la estructura Candle con el atributo # __slots__ que ahorra RAM y hace el acceso a atributos más rápido.

Cambio mi script de obtencion de datos via RestAPI para que no devuelva un DataFrame (pesado), sino una lista limpia de objetos Candle listos para inyectar en un programa que crearé para mantener el histórico inmutable y la vela actual mutable.

Cambio el ingestor.py para que haga una carga inicial antes de abrir el socket.

Creo el programa que mantiene el histórico inmutable y la vela actual mutable en market_state.py

----------------------------------------------------------------------------------------------------------------------------------
Con esta nueva arquitactura, necesito seuguir una serie de pasos para correr el programa:
    1. Levantar postgres: docker run --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres_db -p 5432:5432 -d postgres:13
    2. Crear base de datos:  docker exec -it pg-test psql -U postgres -c "CREATE DATABASE postgres_db;"
    3. Levantar redis: docker run --name redis-bus -p 6379:6379 -d redis:alpine
    4. Vairifcar levantamiento: docker ps
    5. Ejecutar persister
    6. Ejecutar ingestor

----------------------------------------------------------------------------------------------------------------------------------
Error: Al pasar por Redis mi dataclass Registro, estoy enviando un objeto Python (dataclass) directamente a Redis, pero Redis solo entiende texto o diccionarios.
Modifico mi modelo Registro para incluir un método que devuelva un diccionario puro. Esto es mucho más rápido que usar librerías de reflexión.
Cambio el script que ingiere datos del socket para pasar a diccionario los datos normalizados

----------------------------------------------------------------------------------------------------------------------------------

El activo HYPEUSDT no existe en Binance, detectado por mi error handling en el script binance_rest.py "except Exception as e:
            print(f"Error descargando histórico para {symbol}: {e}")
            return []"
por lo tanto se sustituye por "DOTUSDT"

Tengo silencio por parte del programa al conectar via socket  (binance_socket.py), introduzco logging para ver donde está el fallo.
Gracias a esto veo que no está fallado, simplemente está ingiriendo datos

----------------------------------------------------------------------------------------------------------------------------------
Al ver la base de dato, veo que no se están calculando la volatilidad ni el precio de reserva, modifico la función de persistencia y la del precio de reserva
Cambio el fichero ingestor.py para que calcule la volatilidad y el precio de reserva

----------------------------------------------------------------------------------------------------------------------------------
Estrategias
----------------------------------------------------------------------------------------------------------------------------------

Uso VectorBT para crear estrategias por su rapidez en cálculos vectorizados
Creo la el fichero src/core/strategies/base.py donde implemento la metaclase y el decorador necesarios por el proyecto para validar correcta definicion de estratrgias y medición del tiempo de ejecución.

El decorador será un medidor de latencia de las estrategias para poder indicar el número de datos con el que testear los parámetros óptimos de las estrategias.

La metaclase se encargará de asignar un ID a cada estrategia para poder identificarla.

Modificamos dos dunder methods:
    1. __lt__ para que pueda ordenar listas desordenadas en el socket
    2. __sub__ para obtener el cambio de precios de vela actual menos vela previa
    

Usaré numba para optimizar los cálculos y Grid Search Vectorizado para optimización de parámetros.
instalo numba.


---------------------------------------------------------------------------------------------------------------------------------- 
Creo el script src/core/strategies/math_numba.py y lo invoco en el optimizador de parámetros optimizer.py desde donde escogeré los mejores parámetros para cada estrategia y activo.

Desde la función portfolio_manager.py leo el JSON con los mejores parámetros por activo y estrategia  

Por exceso de complejidad, calculo los parámetros de la estrategia unicamente para velas de 1m para mostrar actividad.

----------------------------------------------------------------------------------------------------------------------------------
Trader Engine
----------------------------------------------------------------------------------------------------------------------------------
Necesito crear el script cerebro del programa, este se encargará de los siguiente:
    1. Mantener el portfolio
    2. Ejecutar las señales que le vienen de "portfolio_manager.py" 
    3. Actualizar valor de portfolio
    4. Registro del trade en memoria
    5. Retornar curva de capital
    6. Retornar tabla de trades

Como al calcular el resevation price necesito la cantidad en inventario de cada activo y posteriormente este precio al que se entra en el trade. Necesito un feedback loop.

Añado la función de actualizar inventario en la clase ReservePrice.
Añado un getter del inventario en el tradingEngine.

Al introducir parámetros como la fee a pagar en ejecución, me surgió la pregunta sobre el price impact, para ello investigo como la aforntan tanto "takers" como "makers" y me doy cuenta de que el precio de reserva calculado es el que tiene un market-maker.

Modelizo la fee a pagar mediante el precio de mercado +/- (half spread + exchange fee + Impact)
Donde El impacto se modeliza como coeficiente de impacto * vol * sqrt(Qty/Volumen).
El coeficiente de impacto es calibrable pero excede el scope del proyecto.

Creo las funciones auxiliares de reporte de trades y curva de capital.

Me surgen dudas sobre el sizing del trade, con las piezas clave del precio de reserva y el price impact, intento encontrar una Q que maximice el beneficio de la siguiente forma:
    1. Mi edge (delta) será | precio reserva (pr) - Pmkt | - FeeExchange
    2. Por lo tanto el beneficio (pi) será de: Q*delta - Q*(Y*sigma*sqrt(Qty/Volumen))
    3. Optimizo respecto a Q -> delta - (3/2)*(Y*sigma/sqrt(Volumen)) * sqrt(Q) = 0
    4. Q* = (4/9)*(delta^2*Volumen)/(Y*sigma)^2.

Introduzco un tamaño máximo de orden para evitar pérdidas en un 5% del capital disponible.
Ejecuto pruebas en demo_trade_lifecycle.py pero veo que Q* explota debido a los órdenes de magnitud de delta y sigma.

Exploro el sizing mediante un método combinado de volatility targeting y maximum marticipation rate donde el tamaño de la orden Q* será min(RiskBudget/(Pmkt*sigma_i); 10%*VolumenTotal_i).
Intento aprovechar la información que proporciona el reservation price para calcular el tamaño de la orden Q* óptima. Busco cuantas desviaciiones típicas tenemos de diferencia con el mercado y la normalizo con lo que consigo un multiplicador, edge = | rp - Pmkt | / (Pmkt*sigma)
base = RiskBudget/(Pmkt*sigma_i)
De esta forma, Q* = min(base * edge, 10%*VolumenTotal_i)

Uso __slots__ para optimizar el tamaño de la memoria sustituyendo __dict__ lo cual es crucial si en u nfuturo quiero aumentar el numero de pares tradeables

Creo un integration test que hace mocks para datos y estrategias y ejecuta el trading engine por lo tanto un trade se ejecuta si se cumple lo siguiente:
    1. Estrategia: "¡Quiero comprar!" (Signal=1) ✅ SÍ
    2. Reloj: "¿Pasó 1 min?" ✅ SÍ
    3. Contable: "¿Ganamos más que la Fee?" ✅ SÍ
    4. Matemático ($Q^*$): "¿El tamaño de la apuesta es lógico?" ✅ SÍ
    5. Risk Manager: "¿Es seguro para la cuenta?" ✅ SÍ


----------------------------------------------------------------------------------------------------------------------------------
API vía FastAPI
----------------------------------------------------------------------------------------------------------------------------------
En la carpeta src/api creo los ficheros:
    1.main.py (punto de entrada de la APP)
    2.schemas.py (CREO que modelos definen qué formato de JSON enviará la API al Frontend.)
    3.routes.py (conexión via HTTP con la bbdd)

instalo fastapi, uvicorn y pydantic

Debo modificar el script repository.py para que pueda leer de la BBDD las velas descargadas via rest API,  los trades ejecutados y las métricas

Para poder levantar la API, necesito teenr un Dockerfile, para ello lo enlazo con uv ya que es el dependency manager que estoy usando
Comando: docker-compose up -d --build api.

Luego continuo con el desarrollo de la API

----------------------------------------------------------------------------------------------------------------------------------
Necesidades auxiliares
----------------------------------------------------------------------------------------------------------------------------------
Hay que descargar más datos via RestAPI para mayor poder de backtesting mientras -> necesidad de manejo errores HTTP 418 y 429:
    418: "Soy una tetera" Originalmente es una broma del protocolo HTTP ("Soy una tetera, no puedo hacer café"), pero Binance lo usa para indicar un Baneo de IP Automático.
    429: Demasiadas request -> introducir pausas en mi bucle de forma inteligente -> leer el header "retry-after" ya que Binance indicará cuanto tiempo debo esperar.
    
Modifico el script binance_rest introduciendo el método "_make_request" para saber cuando realizar peticiones y manejar los errores HTTP 418 y 429.

Así mismo necesito usar tenacity (facilita lógica de reintentos en conexiones inestables como el socket) para mejorar el exponential backoff del socket. Para ello introduzco el decorador @retry con estrategia de espera exponencial y triggers para connectionClosed, Error de interntet o timeout del socket.

modifico websockets.connect(uri) introduciendo ping_interval y ping_timeout para detectar la conexión perdida.
Para testear la correcta funcionalidad de estas nuevas funciones, ejecuto mi script ingestor.py, dejo que baje datos via REST, dejo que baje algunos datos via socket y desconecto el wifi para probar la funcionalidad del reintentos salen los siguientes prints- >⚡ Procesados 1000 ticks... (Último: BTCUSDT)
⚠️ Conexión perdida. Reintentando en 1.0s... (Intento #1)
Concenctando a Binance para 10: ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'SOLUSDT', 'TRXUSDT', 'DOGEUSDT', 'ADAUSDT', 'LINKUSDT', 'DOTUSDT']
⚠️ Conexión perdida. Reintentando en 2.0s... (Intento #2)
Concenctando a Binance para 10: ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'SOLUSDT', 'TRXUSDT', 'DOGEUSDT', 'ADAUSDT', 'LINKUSDT', 'DOTUSDT']
⚠️ Conexión perdida. Reintentando en 4.0s... (Intento #3)
-> Aquí reconecto el Wifi
Concenctando a Binance para 10: ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'SOLUSDT', 'TRXUSDT', 'DOGEUSDT', 'ADAUSDT', 'LINKUSDT', 'DOTUSDT']
✅ Conectado. Esperando datos...
⚡ Procesados 100 ticks... (Último: BTCUSDT)
⚡ Procesados 200 ticks... (Último: LINKUSDT)

Funciona Ok

#################################
Necesito meter reservation price en la base de datos RESTAPI para poder realizar las estrategias con una unica fuente de verdad
#################################
Modifico los scripts de la carpeta database y el script de models, introduciendo la volatilidad y el precio de reserva en la tabla de velas.
Cuando meto cmpos nuevos en las BBDD ,ecesito volver a crear los contenedores: docker-compose down -v && docker-compose up -d


modifico el script ingestor.py para configurar todos los simbolos a la vez evitando bucles for y usando asyncio.gather para paralelizar la carga de datos.


Necesito un script que coordine la ingesta de datos via socket acumulando datos cada minuto, no calcular estrategias hasta no tener la vela cerrada y el encargado de llamar a la bbdd cuando ocurra un trade.

Creo el método add_candle en market_state.py para agregar las velas cerradas cada minuto 

Mi docker no encuentra el archivo con lo parámetros de cada estrategia, añado el volumen de código a mi docker-compose.yaml

#############################
Sigo con la creación de endpoints de la API
#############################

En routes.py accedo a los atributos de las velas, creo endpoint para identificar los simbolos disponibles (get_symbols), para obtener las pnl (get_pnl) y posiciones (get_positions)


#####################################
Creación del front end via React Vite
#####################################

Con npx -y create-vite@latest creo el proyecto en la carpeta frontend con el package.json, vite.config.js, index.html, el directorio src y un componente App.jsx

Una vez creados los endpoints, utilizo librerías de TradgingView

Creo una layout tal que: 
┌────────────────────────────────────────┐
│              HEADER                    │
├──────────────────┬─────────────────────┤
│  Bid/Ask Chart   │  Candlestick Chart  │
│  (evolución)     │  (minutos)          │
├──────────────────┴─────────────────────┤
│           TRADES TABLE                 │
├────────────────────────────────────────┤
│           METRICS (PnL Cards)          │
└────────────────────────────────────────┘



##########
Creo el script start.sh para levantar todo el sistema con un solo comando
