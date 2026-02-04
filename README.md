Documentación posteriormente creada con Sphinx

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
    418:  Binance lo usa para indicar un Baneo de IP Automático.
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

Publico los trades vía Redis para que el frontend se actualice instantáneamente
#############################
Sigo con la creación de endpoints de la API
#############################

En routes.py accedo a los atributos de las velas, creo endpoint para identificar los simbolos disponibles (get_symbols), para obtener las pnl (get_pnl) y posiciones (get_positions)


#####################################
Creación del front end via React Vite
#####################################

Se ha seleccionado React + Vite para garantizar una experiencia de usuario sin bloqueos (non-blocking UI). Dado que el dashboard debe reflejar cambios en el libro de órdenes y el PnL con una latencia inferior al tiempo de procesamiento del motor. Vite nos permite una arquitectura modular donde la visualización no interfiere con la consistencia de los datos.

Con npx -y create-vite@latest creo el proyecto en la carpeta frontend con el package.json, vite.config.js, index.html, el directorio src y un componente App.jsx

Una vez creados los endpoints, utilizo librerías de TradgingView

Creo una layout tal que: 
┌────────────────────────────────────────┐
│              HEADER                    │
├──────────────────┬─────────────────────┤
│  Bid/Ask Chart   │  Candlestick Chart  │
│  (evolución)     │  (según alpha decay)│
├──────────────────┴─────────────────────┤
│           TRADES TABLE                 │
├────────────────────────────────────────┤
│           METRICS (PnL Cards)          │
└────────────────────────────────────────┘

Además creo dropdown para elegir por símbolo, por estrategia y para poder filtrar por fechas

A su vez, sgún la estrategia seleccionada, se mostrarán los parámetros correspondientes y se graficarán las MA



##########
Creo el script start.sh para levantar todo el sistema con un solo comando


Ingestor → Redis Stream → Persister → PostgreSQL
     ↓
Redis Pub/Sub (canal separado) → API WebSocket → Frontend


Debo introducir la funcnión e eliminar registro de trades en repository.py
Elimino la posibilidad de ejercer trades en la primera vela


#####################
Introducción de Alpha Decay 
###################
Motivación: tras intercambiar correos, es razonable y más cerano a la realidad imponer el intervalo como resultante de un cierto alpha decay, no arbitrariamente en un minuto. Debo ir mutando el periodo en función del alpha decay de las estrategias. 
Entiendo que en un entorno real, el intervalo de tiempo de las velas no es constante, sino que varía en función de la volatilidad del mercado. Pero la implementación de un alpha decay ueda fuera de scope


###################
Cambio de Hype por Dot
###################
Resolución de conflictos que surgen cuando un símbolo no existe en Binance.
Puedo irme por dos caminos:
    1. Utilizando una arquitectura hexagonal  usando una metaclase para registrar proveedores como estoy haciendo, añadiendo por ejemplo Coinbase
    2. Utilizando web3.js podemos consultar el latestRoundData de Chainlink para obtener el precio del activo pero obtenemos una latencia mayor que desde un CEX



##################
Solucion de errores en posiciones abiertas y PnL
##################

Implemento la persistencia completa del estado del TraderEngine via Redis Pub/Sub aprovechándolo como borker de mensajería entre Backend y la API

Además impongo la condición de unicamente poder tradear con las velas que vienen del socket para evitar incongruencias


#####################
Requerimientos Excelencia
#####################

1. MyPy para asegurar que los datos que fluyen por la arquitectura hexagonal sean del tipo correcto antes de ejecutar el código
    Instalo mypy 


2. Ruff para uamentar legibilidad d código y seguir estándares de la industria
    Instalo ruff y lo ejecuto: "ruff check . --fix"
    Detecta varios errores de importación y de tipado
    La mayoría de errorres son de tipado para mejorar la legibilidad del código pero hay algunos respecto a la gestión de errores que arreglo capturando el tipo de error específico en lugar de usar bare except
    El unico "error" que no soluciono es el de la variable ambigua O en optimizer.py

3. Uso Sphinx para generar documentación
    Instalo sphinx sphinx-rtd-theme myst-parser, este ultimo para pasar la memoria que he ido haciendo en el REadme
    Para actualizar la documentación: make html




4. Medidas de latencia
    Lo implemento directamente con la IA, creo 1000 operacinoes simuladas, dando los siguientes resultados:
    ======================================================================
    📊 PERFORMANCE METRICS SUMMARY
    ======================================================================

    🖥️  SYSTEM RESOURCES
    CPU:    0.0%
    Memory: 29.7 MB (0.2%)

    ⏱️  LATENCY (ms)
    ----------------------------------------------------------------------
    Operation                    Count      P50      P95      P99     Mean
    ----------------------------------------------------------------------
    process_tick                  1000   0.7048   1.1400   1.2109   0.6970
    strategy_calculate            1000   1.4524   2.1707   2.2503   1.4639
    db_write                      1000   3.3017   5.1386   5.3497   3.2850

    🚀 THROUGHPUT (ops/sec)
    process_tick: 181.56
    strategy_calculate: 181.55
    db_write: 181.54


5. Herramientas de profiling
    Utilizo las 3 herramientas proporcionadas por el profesor, el profiling es una técnica de análisis dinámico que miden el rendimiento de un programa mientras se ejecuta cuyo objetivo es identificar qué partes del código consumen más recursos, permitiéndote optimizar con precisión.
    cProfile: más básico, viene integrado en python
    py-spy: para procesos en vivo, se pueden generar flamegraphs. En este caso, vemos que se gasta bastante tiempo para importar librerías y a la inicialización de módulos
    scalene: para línea por línea


6. OpenTelemetry
    Sigue el recorrido de una petición a ttravés de todo el sistema, mide latencias y permite correlacionar logs con traces.
    En nuestro caso podeos usarla para medir diferencias entre Event time e Ingestion time
    

7. CI/CD
    Ya tengo docker-compose, lo he ido haciendo con el proyecto, me falta el script de terraform para desplegarlo en AWS.
    Defino los requisitos: suficiente ram como para correr PostgreSQL, Redis, la API y el frontend. 
    Defino los bloques minimos: 
        terraform {}     # Versión y providers requeridos
        provider "aws" {} # Configuración del proveedor cloud
        variable {}      # Variables parametrizables
        data {}          # Datos externos (ej: buscar AMI más reciente)
        resource {}      # Recursos a crear
        output {}        # Valores de salida (IPs, URLs, etc.)
    Elijo aws y eu-west-1
    Defino las reglas de firewall: 
        resource "aws_security_group" "hesperides_sg" {
            ingress { port = 22 }   # SSH
            ingress { port = 8000 } # API
            ingress { port = 3000 } # Frontend
            egress { all }          # Permitir salida
        }

    Ahora habría que instalar terraform y ejecutar los siguuientes comandos:
    terraform init
    terraform plan
    terraform apply



## Respuestas a preguntas no contestadas previamente

### 1. Ordenación temporal, latencia y relojes distribuidos

**1. Detección de información bajada via WebSocket desordenada:**
Binance puede entregar mensajes fuera de orden porque usa múltiples servidores con relojes ligeramente desincronizados. En mi código, la clase `DataGuard` (en `binance_socket.py`) detecta esto comparando `new_tick.time < self._last_state.time`. Si el timestamp del nuevo tick es menor que el último procesado, lo descarto y aumento el contador `_dropped_out_of_order`.

**Ejemplo concreto:** Si recibo tick1 con t=1000ms, luego tick2 con t=998ms (llegó tarde desde otro servidor), mi guard lo detecta y descarta tick2.

**2. Event time vs Ingestion time:**
- **Event time**: Momento en que el evento ocurrió en el exchange (timestamp de Binance)
- **Ingestion time**: Momento en que mi sistema recibe y procesa el mensaje

**¿Cuál usar?** Event time para cálculos de estrategias porque refleja el momento real del mercado. Uso ingestion time (`time.time()`) para monitorizar latencia del pipeline.

**3. Reconstrucción de flujo temporal coherente:**
- **Buffer:** Acumulo N segundos de datos, ordeno por timestamp, proceso en orden. **Ventaja:** Garantiza orden perfecto. **Desventaja:** Añade latencia fija.
- **Corrección incremental:** Proceso inmediatamente, si llega uno fuera de orden, lo descarto o corrijo estado. **Ventaja:** Baja latencia. **Desventaja:** Puede perder datos.

Mi implementación usa corrección incremental (descarte) porque la latencia es prioritaria en trading.

**4. Clock drift:**
Desviación progresiva entre relojes de diferentes sistemas. El timestamp del backend es autoritativo cuando: (a) el exchange no proporciona timestamp, (b) necesitamos medir latencia del pipeline, (c) ordenar eventos de múltiples exchanges.

**5. Test determinista de monotonicidad:**
```python
def test_monotonicity_violation():
    guard = DataGuard()
    tick1 = Registro(time=1000, ...)
    tick2 = Registro(time=998, ...)  # Fuera de orden
    
    assert guard.monotonicity_duplicates(tick1) == True
    assert guard.monotonicity_duplicates(tick2) == False  # Rechazado
    assert guard._dropped_out_of_order == 1
```

---

### 2. Persistencia, idempotencia y eliminación de duplicados

**5. Detección de duplicados y primary identity de un trade:**
La primary identity de un trade es la combinación `(symbol, timestamp, price, quantity)`. En mi `DataGuard`, detecto duplicados comparando todos los campos del tick (bid/ask price + quantities). Si son idénticos al último, es duplicado.

**6. Idempotencia:**
Una operación es idempotente si ejecutarla múltiples veces produce el mismo resultado. En mi ingestor, usar `INSERT ... ON CONFLICT DO NOTHING` garantiza que reintentos tras una reconexión no dupliquen datos.

**Caso de duplicados sin idempotencia:** Si el socket se desconecta justo después de enviar datos a Redis pero antes de confirmar, la reconexión reenviaría los mismos datos duplicándolos.

**6. Esquema para garantizar unicidad:**
```sql
CREATE TABLE book_ticks (
    symbol VARCHAR(20),
    event_time BIGINT,
    bid_price DECIMAL,
    PRIMARY KEY (symbol, event_time)  -- Unicidad compuesta
);
```
El PRIMARY KEY compuesto evita duplicados bajo concurrencia.

**7. Condiciones de carrera en inserción:**
Uso `asyncio.Lock` cuando múltiples corrutinas acceden al mismo recurso. En PostgreSQL, las transacciones con nivel de aislamiento `SERIALIZABLE` previenen condiciones de carrera. Mi buffer en `repository.py` acumula datos y hace batch inserts atómicos.

---

### 3. Backpressure y control de flujo

**8. Si Binance envía más rápido de lo que proceso:**
Redis Streams actúa como buffer elástico entre ingestor y persister. Si el consumidor (persister) no puede seguir el ritmo, los mensajes se acumulan en Redis. Eventualmente, si Redis alcanza su límite de memoria, comenzaría a descartar mensajes antiguos (política `maxmemory-policy volatile-lru`).

**9. Detección de lag:**
```python
# En el consumidor
last_processed_id = await redis.xread(...)
stream_info = await redis.xinfo_stream('ticks')
pending = stream_info['length'] - processed_count
if pending > 1000:
    logger.warning(f"Consumer lag: {pending} mensajes pendientes")
```

**10. Bounded queues con drop oldest vs rate limiting:**
- **Drop oldest**: Descarta mensajes antiguos cuando la cola está llena. **Sesgo:** Pierdes historia, tus MAs serán incorrectas.
- **Rate limiting**: Ralentizas la entrada. **Sesgo:** Pierdes ticks recientes, tu sistema va "retrasado" respecto al mercado.

Mi elección: Bounded queue con alertas pero sin drop, preferible ralentizar temporalmente.

**11. Métricas de lag y alertas:**
```python
# Métrica
lag_seconds = (time.time() * 1000) - last_event_time
# Alerta
if lag_seconds > 5:
    send_alert("Pipeline lag > 5s")
```

**12. Reequilibrio de throughput bajo carga extrema:**
1. Escalar horizontalmente (más consumidores por partición)
2. Reducir granularidad (agregar antes de persistir)
3. Mover cálculos pesados a procesos separados con multiprocessing

---

### 4. Consistencia eventual vs consistencia fuerte en PnL

**13. Qué partes necesitan consistencia fuerte:**
- **Ejecución de trades**: El saldo disponible DEBE estar sincronizado antes de ejecutar
- **Cálculo de posición actual**: Necesita trade log completo y ordenado
- **Risk limits**: Verificar margen antes de nueva orden

**14. Ejemplo de PnL incorrecto por inconsistencia:**
Si ejecuto una venta de BTC pero la base de datos aún no reflejó la compra previa, mi cálculo de PnL mostraría una "venta descubierta" con beneficio ficticio negativo.

**15. Condiciones de carrera en cálculos de PnL:**
Dos routines actualizando el mismo saldo: Thread A lee saldo=100, Thread B lee saldo=100, ambos suman 10, resultado=110 (debería ser 120). Solución: `asyncio.Lock` o transacciones atómicas en PostgreSQL.

**16. Tests unitarios para invariantes de PnL:**
```python
def test_pnl_invariant():
    engine = TraderEngine(initial_usdt=10000)
    engine.execute_trade("BUY", "BTCUSDT", 1.0, 50000)
    engine.execute_trade("SELL", "BTCUSDT", 1.0, 51000)
    
    # Invariante: PnL = cash_final - cash_inicial + valor_posiciones
    assert engine.get_equity() == 10000 + (51000 - 50000)  # Profit
```

---

### 5. Modelado avanzado de posiciones

**17. Actualizar precio medio tras partial fills:**
```python
# Posición actual: 2 BTC @ 50000
# Nuevo fill: 1 BTC @ 52000
new_qty = 2 + 1  # = 3
new_avg_price = (2 * 50000 + 1 * 52000) / 3  # = 50666.67
```
Implementado en `TraderEngine` con `update_position()`.

**18. Reconstruir posición desde log de trades:**
```python
def rebuild_portfolio(trades: List[Trade]) -> Dict[str, Position]:
    positions = {}
    for trade in sorted(trades, key=lambda t: t.timestamp):
        symbol = trade.symbol
        if trade.side == "BUY":
            positions[symbol].qty += trade.qty
        else:
            positions[symbol].qty -= trade.qty
        # Recalcular avg_price...
    return positions
```
Datos imprescindibles: timestamp, symbol, side, qty, price.

**19. Problemas al mezclar conceptos Binance con dominio:**
Si mi entidad `Trade` tiene un campo `binance_order_id`, el dominio queda acoplado a Binance. Al integrar otro exchange (Coinbase), tendría que modificar el core. Solución: El adaptador traduce `binance_order_id` a un `exchange_order_id` genérico.

---

### 6. Concurrencia, asincronismo y paralelismo

**20. Cuándo usar asyncio vs threads:**
- **asyncio**: Para operaciones I/O-bound (WebSockets, HTTP, DB queries). Un solo thread maneja miles de conexiones.
- **threads**: Para librerías que no soportan async (algunas DB drivers). También para CPU-bound si el GIL no es problema.
- **multiprocessing**: Para CPU-bound pesado (backtesting, optimización de estrategias).

**21. Qué problema resuelve el GIL:**
El Global Interpreter Lock impide que dos threads ejecuten bytecode Python simultáneamente, evitando corrupciones de memoria. Afecta a mi sistema porque cálculos CPU-bound (Numba) no se benefician de threads → uso multiprocessing o Numba que libera el GIL.

**22. Evitar que función bloqueante congele event loop:**
```python
# MAL: Bloquea todo el event loop
result = heavy_cpu_function()

# BIEN: Ejecutar en thread pool
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, heavy_cpu_function)
```

**23. Pipeline con asyncio.Queue:**
```
Ingestor → asyncio.Queue → Processor → asyncio.Queue → Persister
```
Cada stage es una corrutina que hace `await queue.get()`, procesa, y hace `await next_queue.put()`.

**24. Race condition con await:**
```python
# Problema: Entre el await y el uso, otro task puede modificar
balance = await get_balance()  # = 100
# <-- Otro task resta 50 aquí
await spend(balance)  # Gasta 100, pero solo había 50

# Solución: Lock
async with balance_lock:
    balance = await get_balance()
    await spend(balance)
```

**25. Medir latencia del event loop:**
```python
import time
async def measure_loop_latency():
    start = time.perf_counter()
    await asyncio.sleep(0)  # Yield al loop
    latency = time.perf_counter() - start
    if latency > 0.1:
        logger.warning(f"Event loop lag: {latency*1000:.2f}ms")
```

---

### 7. Uso avanzado de Python


**26. `__enter__`/`__exit__` para consistencia transaccional:**
```python
class AtomicUpdate:
    def __init__(self, engine):
        self.engine = engine
        self.snapshot = None
    
    def __enter__(self):
        self.snapshot = self.engine.get_state_copy()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:  # Si hubo error, rollback
            self.engine.restore_state(self.snapshot)
        return False
```

---

### 8. Escalado horizontal y multiactivo

**27. Qué rompe al pasar de 10 a 300 activos:**
- **WebSocket**: Binance limita a 1024 streams por conexión → necesito múltiples conexiones
- **CPU**: 300 estrategias calculando en paralelo → bottleneck
- **Memoria**: 300 MarketStates con historial → ~30x más RAM
- **DB**: 30x más writes → posible saturación de PostgreSQL

**28. Límites de CPU, IO, memoria:**
- **CPU**: Numba ayuda, pero 300 símbolos × 3 estrategias = 900 cálculos/minuto
- **IO**: Redis Streams soporta ~100k msg/s, PostgreSQL ~10k inserts/s batch
- **Memoria**: Cada MarketState con 1000 velas ≈ 80KB × 300 = 24MB (manejable)

**29. Particionar procesamiento por símbolo:**
```python
# Sharding: símbolos A-M → Worker 1, N-Z → Worker 2
shard = hash(symbol) % num_workers
await workers[shard].process(tick)
```

**30. Arquitectura con réplicas sin duplicar trabajo:**
Usar Redis Streams con Consumer Groups: cada mensaje se entrega a UN solo consumidor del grupo, evitando duplicación.

---

### 9. Tolerancia a fallos y recuperación

**31. ¿At least once, at most once o exactly once?**
Mi sistema es **at least once**: si Redis falla después de recibir el mensaje pero antes del ACK, lo reenviaré. Acepto posibles duplicados que filtro con idempotencia.

**32. Qué ocurre si persistencia falla:**
Los mensajes se acumulan en Redis Stream (buffer). Cuando PostgreSQL vuelve, el persister consume el backlog. Riesgo: si Redis también falla, pierdo datos en memoria.

**33. Recuperación determinista tras fallo:**
1. Al reiniciar, leo último `message_id` persistido
2. Hago `XREAD` desde ese ID
3. Reproceso todos los mensajes pendientes
4. Estado final idéntico al pre-fallo

**34. Evitar corrupción durante caída abrupta:**
- PostgreSQL usa WAL (Write-Ahead Log) para transacciones atómicas
- Redis con AOF (Append-Only File) para durabilidad
- Nunca modifico archivos in-place, uso atomic rename

---

### 10. Pruebas avanzadas

**35. Qué es un fake exchange:**
Un mock que simula respuestas del exchange real sin conexión a internet. Permite tests deterministas y rápidos.
```python
class FakeExchange:
    def __init__(self, predefined_ticks):
        self.ticks = predefined_ticks
    async def subscribe(self):
        for tick in self.ticks:
            yield tick
```

**36. Test determinista con generador de eventos:**
```python
def test_pipeline_deterministic():
    ticks = [
        Registro(time=1, price=100),
        Registro(time=2, price=101),
    ]
    fake = FakeExchange(ticks)
    result = run_pipeline(fake)
    assert result == expected_output  # Siempre igual
```

**41. Simular condiciones de red adversas:**
```python
class UnreliableExchange(FakeExchange):
    async def subscribe(self):
        for i, tick in enumerate(self.ticks):
            if i == 5:
                await asyncio.sleep(2)  # Latencia
            if i == 10:
                raise ConnectionError()  # Desconexión
            yield tick
```

**42. Verificar reproducibilidad del pipeline:**
```python
def test_reproducibility():
    input_data = load_fixture("ticks.json")
    
    result_1 = run_pipeline(input_data, seed=42)
    result_2 = run_pipeline(input_data, seed=42)
    
    assert result_1.trades == result_2.trades
    assert result_1.final_pnl == result_2.final_pnl
```




### Flujo de Información Detallado

┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTA DE DATOS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Binance REST ──► BinanceRest ──► Candle[] ──► MarketState (histórico)     │
│  Binance WS   ──► BinanceDriver ──► DataGuard ──► Redis Stream             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PROCESAMIENTO                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Redis ──► Persister ──► MarketState.update() ──► Candle actual            │
│                              │                                               │
│                              ▼                                               │
│                    ReservePrice.calculate()                                  │
│                              │                                               │
│                              ▼                                               │
│              ┌───────────────┼───────────────┐                              │
│              ▼               ▼               ▼                              │
│        MACrossStrategy  MomentumStrategy  CandlePattern                     │
│              │               │               │                              │
│              └───────────────┼───────────────┘                              │
│                              ▼                                               │
│                    PortfolioManager.evaluate()                              │
│                              │                                               │
│                              ▼                                               │
│                    TraderEngine.execute()                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PERSISTENCIA                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  TraderEngine ──► PostgreSQL (trades, candles)                              │
│  TraderEngine ──► Redis Pub/Sub (estado en tiempo real)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI                                                                     │
│    ├── GET /candles/{symbol} ──► PostgreSQL                                 │
│    ├── GET /trades ──► PostgreSQL                                           │
│    ├── GET /positions ──► Redis                                             │
│    ├── GET /pnl ──► Redis + PostgreSQL                                      │
│    └── WS /ws/ticks ──► Redis Pub/Sub                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  React + Vite                                                                │
│    ├── CandlestickChart ◄── /candles + señales                              │
│    ├── BidAskChart ◄── WebSocket /ws/ticks                                  │
│    ├── TradeTable ◄── /trades                                               │
│    ├── PositionsTable ◄── /positions                                        │
│    └── PnLCards ◄── /pnl                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Clases Principales y Responsabilidades

| Clase | Responsabilidad | Dunder Methods |
|-------|-----------------|----------------|
| `DataGuard` | Filtra duplicados y valida monotonicidad | - |
| `Registro` | Dataclass para tick del order book | `to_dict()` |
| `Candle` | Dataclass OHLCV con volatilidad | `__lt__`, `__sub__` |
| `MarketState` | Buffer de velas históricas + actual | - |
| `ReservePrice` | Cálculo Avellaneda-Stoikov | - |
| `StrategyMeta` | Metaclase que valida ID de estrategias | `__new__` |
| `BaseStrategy` | ABC con `@measure_latency` | - |
| `PortfolioManager` | Agrega señales de todas las estrategias | - |
| `TraderEngine` | Ejecuta trades y gestiona riesgo | - |



