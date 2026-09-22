# Motor de reportes estratégicos con IA

Genera reportes ejecutivos de performance publicitaria a partir de datos de
campañas: lee las métricas, las calcula, y usa la API de Gemini para redactar
un informe con KPIs, hallazgos y plan de acción priorizado.

Reescritura en Python de una automatización que construí originalmente en Make.
El objetivo de la reescritura fue entender qué hace una plataforma no-code por
debajo — y hacerlo mejor en los tres puntos donde no-code se queda corto:
manejo de errores, reintentos y validación de la salida del modelo.

```
Datos de campañas          Cálculo de métricas         Redacción            Entrega
(Google Sheets / CSV)  ->  (ROAS, CPA, semáforo)  ->  (Gemini API)  ->  (Google Docs / HTML)
                            en Python, no en el LLM      con reintentos      
```

## Decisiones de diseño

**El modelo no calcula.** Todos los ROAS, CPA y totales se computan en
`metricas.py` y se le entregan ya resueltos al prompt. Un LLM sumando columnas
de dinero es un bug esperando a ocurrir: la aritmética es determinista y barata,
la redacción no. El modelo solo hace aquello en lo que es bueno.

**La respuesta del modelo se valida antes de usarse.** `validacion.py` verifica
que el HTML esté completo, que empiece y termine donde debe, y que contenga las
cuatro secciones obligatorias. Si el modelo devuelve markdown, se corta a media
frase o se salta el plan de acción, no llega al documento del cliente.

**Se reintenta solo lo que tiene sentido reintentar.** Un 429 o un timeout son
transitorios: backoff exponencial con jitter. Un 401 por API key inválida
fallaría igual las tres veces, así que falla de inmediato con un mensaje claro.

**Las fuentes y los destinos son intercambiables.** `FuenteCSV` permite
desarrollar y testear sin credenciales ni red; `FuenteGoogleSheets` es la de
producción. Lo mismo con `DestinoArchivo` y `DestinoGoogleDocs`.

## Uso

```bash
pip install -r requirements.txt
cp .env.example .env    # y completa GEMINI_API_KEY

# Solo las métricas, sin llamar a la API (no gasta cuota)
python -m src.main --cliente NovaShop --solo-metricas

# Reporte completo a un archivo HTML local
python -m src.main --cliente NovaShop

# Leyendo de Google Sheets y publicando en Google Docs
python -m src.main --cliente NovaShop --fuente sheets --destino docs
```

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `src/metricas.py` | Modelo de datos y cálculo de ROAS, CPA, agregados |
| `src/fuentes.py` | Lectura desde CSV o Google Sheets |
| `src/prompts.py` | Construcción del prompt e instrucción de sistema |
| `src/gemini.py` | Llamada a la API con reintentos y backoff |
| `src/validacion.py` | Verificación del HTML devuelto por el modelo |
| `src/salidas.py` | Escritura a archivo o a Google Docs |
| `src/main.py` | CLI y orquestación |

## Tests

```bash
pytest tests/ -v
```

30 tests sin dependencias de red. Cubren los casos que rompen este tipo de
script en producción: división por cero cuando una campaña no tiene gasto,
celdas vacías o con `$1,200.00` en vez de números, valores en los límites exactos
del semáforo, respuestas del modelo truncadas o envueltas en markdown, y la
diferencia entre un error que conviene reintentar y uno que no.

## Credenciales de Google

Para `--fuente sheets` o `--destino docs`:

1. Crear un proyecto en Google Cloud y habilitar las APIs de Sheets y Drive.
2. Crear una cuenta de servicio y descargar su JSON como `credentials.json`.
3. Compartir la hoja de cálculo con el email de la cuenta de servicio.

`credentials.json` y `.env` están en `.gitignore`. No los subas al repo.

## Formato de los datos

| cliente | campana | plataforma | gasto | impresiones | clics | conversiones | ingresos |
|---|---|---|---|---|---|---|---|
| NovaShop | Black Friday | Meta Ads | 1200.00 | 145000 | 3800 | 190 | 7800.00 |

Ver `data/campanas_ejemplo.csv`.
