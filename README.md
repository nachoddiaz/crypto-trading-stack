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
    2. Crear base de datos:  docker exec -it pg-test psql -U postgres -c "CREATE DATABASE trading_db;"
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