"""Prepara los datos vectoriales del Taller 1.

Salidas en ../datos/:
- focos_firms_uy.zip : shapefile (zip) con focos de calor VIIRS S-NPP 2018-2024 en Uruguay
- taller1_uy.gpkg    : geopackage con departamentos, lavalleja, minas, cuenca_rio_negro
                       y comunicaciones_proyecto

Todo en EPSG:4326 (geoplot trabaja con coordenadas geográficas).
Uso: python 01_vectores.py
"""
import io
import shutil
import tempfile
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import urllib3

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

AQUI = Path(__file__).parent
SALIDA = AQUI.parent / "datos"
CACHE = AQUI / "cache"
SALIDA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)

FIRMS = "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{a}/viirs-snpp_{a}_Uruguay.csv"
OAN = "https://www.ambiente.gub.uy/geoservicios/s2.php?idcapa={}"
IDE = "https://mapas.ide.uy/geoserver-vectorial"
SIMPLIFICAR_M = 100  # tolerancia de simplificación de polígonos, en metros
ESTACIONES = {12: "verano", 1: "verano", 2: "verano", 3: "otoño", 4: "otoño", 5: "otoño",
              6: "invierno", 7: "invierno", 8: "invierno", 9: "primavera", 10: "primavera",
              11: "primavera"}


def descargar(url, nombre, verify=True):
    """Descarga url -> cache/nombre una sola vez."""
    destino = CACHE / nombre
    if not destino.exists():
        r = requests.get(url, timeout=600, verify=verify, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        destino.write_bytes(r.content)
    return destino


def wfs(ws, capa, cql=None):
    """Lee una capa WFS de IDE Uruguay como GeoDataFrame en EPSG:4326."""
    p = dict(service="WFS", version="2.0.0", request="GetFeature", typeNames=f"{ws}:{capa}",
             outputFormat="application/json", srsName="EPSG:5382")
    if cql:
        p["CQL_FILTER"] = cql
    nombre = f"wfs_{capa}{'_filtrado' if cql else ''}.geojson"
    destino = CACHE / nombre
    if not destino.exists():
        r = requests.get(f"{IDE}/{ws}/wfs", params=p, timeout=600)
        r.raise_for_status()
        destino.write_bytes(r.content)
    return gpd.read_file(destino)


def simplificar(gdf):
    """Simplifica en metros (EPSG:5382) y vuelve a EPSG:4326."""
    gdf = gdf.to_crs(5382)
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFICAR_M, preserve_topology=True)
    return gdf.to_crs(4326)


# --- Departamentos (OAN, capa c004) -----------------------------------------------------------
deptos = gpd.read_file(f"zip://{descargar(OAN.format('c004'), 'departamentos.zip', verify=False)}")
deptos = deptos[deptos.nombre != "LÍMITE CONTESTADO"][["nombre", "areakm2", "geometry"]]
deptos = deptos.rename(columns={"nombre": "depto", "areakm2": "area_km2"}).to_crs(4326)
deptos = simplificar(deptos).reset_index(drop=True)
lavalleja = deptos[deptos.depto == "LAVALLEJA"].reset_index(drop=True)

# --- Minas (IDE, localidades censales INE) ----------------------------------------------------
minas = wfs("ideuy", "localidades_censales_ine", "nomloc='MINAS' AND nomdepto='LAVALLEJA'")
minas = minas[["nomloc", "nomdepto", "pob_tot_23", "viv_tot_23", "area_km2", "geometry"]]
minas = minas.rename(columns={"nomloc": "localidad", "nomdepto": "depto",
                              "pob_tot_23": "poblacion_2023", "viv_tot_23": "viviendas_2023"})
minas = minas.to_crs(4326)

# --- Cuenca del Río Negro (IDE, cuencas nivel 2) ----------------------------------------------
cuencas = wfs("ET_CUENCAS_HIDROGRAFICAS", "cn_cuencas_ndc_2_10k")
rio_negro = cuencas[cuencas.nam == "RÍO NEGRO"].dissolve(by="nam").reset_index()
rio_negro = simplificar(rio_negro[["nam", "geometry"]].rename(columns={"nam": "cuenca"}))
rio_negro["area_km2"] = rio_negro.to_crs(5382).area.round(-6) / 1e6

# --- Comunicaciones de Proyecto (OAN, capa c1296) ---------------------------------------------
cp = gpd.read_file(f"zip://{descargar(OAN.format('c1296'), 'comunicaciones_proyecto.zip', verify=False)}",
                   layer="c1296Point")
cp["anio_expediente"] = pd.to_numeric(cp["hex"].str[:4], errors="coerce").astype("Int64")
cp["tipo"] = cp["amb_apl_no"].str.split("- ", n=1).str[1]
# Categoría corta (el `tipo` original es el texto completo del decreto)
CATEGORIAS = {"EXTRACCIÓN DE MINERALES": "minería", "NUEVAS PLANTACIONES FORESTALES": "forestación",
              "TODA CONSTRUCCIÓN U OBRA QUE SE PROYECTE EN LA FAJA": "faja costera",
              "CONSTRUCCIÓN DE UNIDADES O COMPLEJOS INDUSTRIALES": "industria",
              "CONSTRUCCIÓN DE REPRESAS": "represa"}
cp["categoria"] = "otros"
for inicio, cat in CATEGORIAS.items():
    cp.loc[cp.tipo.str.startswith(inicio, na=False), "categoria"] = cat
cp = cp[["pro_nombre", "categoria", "tipo", "clasificac", "hex", "anio_expediente", "geometry"]]
cp = cp.rename(columns={"pro_nombre": "proyecto", "clasificac": "clasificacion", "hex": "expediente"})
cp = cp.to_crs(4326)
# Hay puntos con coordenadas erróneas (p. ej. en medio del Atlántico). Se descartan solo los que caen
# fuera de una caja amplia de Uruguay + su franja marítima; las obras costeras y en el agua se mantienen.
n0 = len(cp)
cp = cp.cx[-59.5:-52.5, -36.5:-29.5].reset_index(drop=True)
print(f"Comunicaciones de Proyecto: {n0 - len(cp)} puntos fuera de la caja de Uruguay descartados")

# --- Focos de calor FIRMS 2018-2024 -----------------------------------------------------------
focos = pd.concat([pd.read_csv(descargar(FIRMS.format(a=a), f"firms_{a}.csv")) for a in range(2018, 2025)],
                  ignore_index=True)
focos = focos[focos.type == 0]  # 0 = vegetación probable
# acq_date + acq_time (HHMM) están en UTC; pasamos a hora de Uruguay (UTC-3)
utc = pd.to_datetime(focos.acq_date) + pd.to_timedelta(focos.acq_time // 100, unit="h") \
    + pd.to_timedelta(focos.acq_time % 100, unit="m")
local = utc - pd.Timedelta(hours=3)
focos = gpd.GeoDataFrame({
    "fecha": local.dt.strftime("%Y-%m-%d"),
    "anio": local.dt.year,
    "mes": local.dt.month,
    "estacion": local.dt.month.map(ESTACIONES),
    "hora": local.dt.hour,
    "dianoche": focos.daynight.map({"D": "día", "N": "noche"}),
    "confianza": focos.confidence.map({"l": "baja", "n": "nominal", "h": "alta"}),
    "frp": focos.frp,
}, geometry=gpd.points_from_xy(focos.longitude, focos.latitude), crs=4326)
# Solo focos dentro de Uruguay, con el nombre del departamento
focos = focos.sjoin(deptos[["depto", "geometry"]], predicate="within").drop(columns="index_right")
focos = focos.sort_values(["fecha", "hora"]).reset_index(drop=True)

# --- Guardar ----------------------------------------------------------------------------------
gpkg = SALIDA / "taller1_uy.gpkg"
gpkg.unlink(missing_ok=True)
for capa, gdf in [("departamentos", deptos), ("lavalleja", lavalleja), ("minas", minas),
                  ("cuenca_rio_negro", rio_negro), ("comunicaciones_proyecto", cp)]:
    gdf.to_file(gpkg, layer=capa, driver="GPKG")

with tempfile.TemporaryDirectory() as tmp:
    focos.to_file(Path(tmp) / "focos_firms_uy.shp", encoding="utf-8")
    zipeado = shutil.make_archive(str(SALIDA / "focos_firms_uy"), "zip", tmp)

print(f"{len(focos)} focos ({focos.fecha.min()} → {focos.fecha.max()}), "
      f"{(focos.depto == 'LAVALLEJA').sum()} en Lavalleja")
print(gpd.list_layers(gpkg))
for f in sorted(SALIDA.glob("*")):
    print(f"{f.name:30s} {f.stat().st_size / 1e6:6.2f} MB")
