# Bitácora de Desarrollo del Proyecto

## 1. Estructura y Configuración
- [ ] Creación de la estructura del proyecto.
- [ ] Creación del entorno virtual.
- [ ] Creación del directorio `Justificaciones_Uso`: Documentación de pros/contras de tecnologías y decisiones.
- [ ] Creación del directorio `Testeo_Strats`: Explicación del proceso de elección de parámetros.

## 2. Pruebas de Almacenamiento (Benchmark)
- [ ] Creación de un script de prueba con el que testear el mejor almacenamiento para implementar la conexión RestAPI **RestAPI**.
### 2.1 [ ] Creación un script de prueba con el que testear el mejor almacenamiento para implementar la conexión socket **WebSocket**.

#### 2.1.1 Dependencias
Instalación de librerías para el módulo de WebSockets:

| Librería | Propósito | Notas |
| :--- | :--- | :--- |
| `websockets` | Conexión socket con Binance | Externa |
| `asyncio` | Gestión de eventos asíncronos | Externa |
| `aiofiles` | Escritura de archivos asíncrona | Externa |
| `json` | Codificación de datos | Nativa Python |
| `time` | Medición de tiempos | Nativa Python |

## 3. Resolución de Problemas (Log)

### Error de Conflicto de Nombres
* **Error:** Llamé al fichero  `socket.py` cuando ya existe una libreria con el mismo nombre .
* **Solución:** Renombrar el archivo.

### Procesamiento de Datos
* **Socket Stream:** Cambio de `@depth` por `@bookTicker`.
    * *Motivo:* Eficiencia. Se obtiene directamente el *Best Bid/Ask* sin procesar todo el libro.
* **Formato de Datos:** Los precios llegan como `string`.
    * *Acción:* Casting obligatorio a `float` para operaciones matemáticas.

## 4. Definiciones Matemáticas y Lógica

### Precio de Ejecución (Fill Price)
* **Pregunta:** ¿Cómo estimar el precio de fill en backtesting?
* **Decisión:** Asumir **Cero Impacto** (Liquidez infinita en el Top of Book).
    * **Compra:** Precio = *Lowest Ask*.
    * **Venta:** Precio = *Highest Bid*.
    * *Nota:* No se modifica el precio según el volumen de la orden.

### Valoración del Activo (Mid-Price Modificado)
* **Modelo:** Avellaneda-Stoikov.
* **Concepto:** El *Reservation Price* ($r$) es la valoración subjetiva ajustada al riesgo del trader, utilizada para sesgar las cotizaciones (*skewing*) y llevar el inventario a cero.

**Fórmula:**
$$r = s - (q \cdot \gamma \cdot \sigma^2)$$

**Donde:**
* $r$: Reservation Price (Precio de Indiferencia).
* $s$: Mid Price real del mercado ($\frac{Bid+Ask}{2}$).
* $q$: Inventario actual (Positivo=Long, Negativo=Short).
* $\gamma$: Aversión al riesgo (Constante configurada).
* $\sigma$: Volatilidad (Calculada sobre ventana temporal $t-x$).

## 5. Glosario
* **Ingestion Time:** Tiempo transcurrido desde la publicación del mensaje en el exchange hasta que el sistema local puede procesarlo.