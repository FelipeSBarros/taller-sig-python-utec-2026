# Taller: Introducción al SIG con Python

Material del taller "Introducción al SIG con Python" de las Primeras Jornadas de Innovación Geoespacial (UTEC, Minas, Lavalleja, 16 de octubre de 2026). A través de ejercicios prácticos en Google Colab aprendemos a cargar, explorar y visualizar datos geográficos con Python.

## Notebook

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FelipeSBarros/taller-sig-python-utec-2026/blob/main/T1_Introduccion_SIG_Python.ipynb)

`T1_Introduccion_SIG_Python.ipynb`: datos vectoriales (shapefile y geopackage), mapas con geopandas, densidad de kernel con geoplot para leer el patrón espacial y espacio-temporal de los focos de calor, y datos ráster (MDT, Sentinel-2 y NDVI). Las celdas marcadas con ✏️ son para completar.

## Datos (`datos/`)

| Archivo | Tipo | Contenido | CRS |
|---|---|---|---|
| `focos_firms_uy.zip` | Shapefile (puntos) | 21.307 focos de calor VIIRS S-NPP en Uruguay, 2018–2024 | EPSG:4326 |
| `taller1_uy.gpkg` | Geopackage (5 capas) | `departamentos`, `lavalleja`, `minas`, `cuenca_rio_negro`, `comunicaciones_proyecto` | EPSG:4326 |
| `mdt_minas.tif` | Ráster monobanda | Modelo digital del terreno de Minas y alrededores (5 m, altitud en metros) | EPSG:5382 |
| `sentinel2_minas.tif` | Ráster multibanda | Sentinel-2 L2A del 28/02/2026, 16 × 16 km centrado en Minas (10 m). Bandas: 1 azul (B02), 2 verde (B03), 3 rojo (B04), 4 infrarrojo cercano (B08). Reflectancia × 10.000 | EPSG:32721 |

### Cómo cargarlos en Colab

```python
import geopandas as gpd
import rasterio

URL = "https://raw.githubusercontent.com/FelipeSBarros/taller-sig-python-utec-2026/main/datos/"
focos = gpd.read_file(URL + "focos_firms_uy.zip")
gpd.list_layers(URL + "taller1_uy.gpkg")
deptos = gpd.read_file(URL + "taller1_uy.gpkg", layer="departamentos")
mdt = rasterio.open(URL + "mdt_minas.tif")
```

### Columnas de `focos_firms_uy`

| Columna | Descripción |
|---|---|
| `fecha` | Fecha de detección (hora de Uruguay, UTC−3), texto `AAAA-MM-DD` |
| `anio`, `mes`, `hora` | Año, mes (1–12) y hora local (0–23) de la detección |
| `estacion` | `verano` (dic–feb), `otoño` (mar–may), `invierno` (jun–ago), `primavera` (sep–nov) |
| `dianoche` | `día` o `noche` (pasada diurna o nocturna del satélite) |
| `confianza` | Confianza de la detección: `baja`, `nominal` o `alta` |
| `frp` | Potencia radiativa del fuego (MW) |
| `depto` | Departamento donde cae el foco |

Solo se incluyen los focos de tipo 0 ("vegetación probable") que caen dentro de Uruguay. Ojo: algunos puntos fijos que se repiten año a año (industrias, canteras, caleras) igual aparecen como tipo 0; reconocerlos es parte de leer el patrón espacial.

### Capas de `taller1_uy.gpkg`

- `departamentos` y `lavalleja`: límites departamentales (simplificados a 100 m), con el área en km².
- `minas`: localidad censal de Minas, con población y viviendas del censo 2023.
- `cuenca_rio_negro`: cuenca del Río Negro en Uruguay, nivel 2 (simplificada a 100 m).
- `comunicaciones_proyecto`: emprendimientos que iniciaron el trámite ambiental (Comunicación de Proyecto) ante el Ministerio de Ambiente, con `categoria` (minería, forestación, faja costera, industria, represa, otros), `tipo` (texto completo), `clasificacion` (A/B/C), `expediente` y `anio_expediente`. Se descartaron 8 puntos con coordenadas erróneas, fuera de Uruguay y de su franja marítima. Ojo: la columna `fecha` original no es la fecha de ingreso del trámite, por eso se usa el año del expediente.

## Fuentes

- **Focos de calor:** NASA FIRMS, VIIRS S-NPP 375 m, archivo anual por país (https://firms.modaps.eosdis.nasa.gov/country/). *We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS), part of NASA's Earth Science Data and Information System (ESDIS).*
- **Departamentos y Comunicaciones de Proyecto:** Observatorio Ambiental Nacional (OAN), Ministerio de Ambiente, capas `c004` y `c1296` (https://www.ambiente.gub.uy/oan/).
- **Minas, cuenca del Río Negro y MDT:** Infraestructura de Datos Espaciales de Uruguay (IDEuy), servicios WFS de `mapas.ide.uy` (localidades censales INE, cuencas hidrográficas nivel 2 y MDT nacional de 2,5 m).
- **Imagen satelital:** contiene datos modificados de Copernicus Sentinel-2 (2026), obtenidos de Earth Search (Element 84, AWS Open Data).

## Cómo se prepararon

Los scripts de `preparacion/` descargan los datos de las fuentes originales y generan los archivos de `datos/`: `01_vectores.py` (shapefile y geopackage) y `02_raster.py` (MDT y Sentinel-2; acepta otra fecha como argumento, p. ej. `python 02_raster.py 2026-02-08`). Requieren `geopandas`, `rasterio` y `requests`.
