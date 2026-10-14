"""Prepara los rásters del Taller 1 (requiere haber corrido 01_vectores.py).

Salidas en ../datos/:
- mdt_minas.tif        : monobanda. MDT nacional de IDE Uruguay (2,5 m), mosaico recortado a Minas
                         + 1 km y remuestreado a RES_MDT m. EPSG:5382, float32, metros.
- sentinel2_minas.tif  : multibanda. Sentinel-2 L2A (Earth Search, COG) recortado a un cuadrado de
                         LADO_S2 km centrado en Minas. Bandas 1-4 = B02 azul, B03 verde, B04 rojo,
                         B08 infrarrojo cercano (10 m). EPSG:32721, uint16, reflectancia x 10000.
Uso: python 02_raster.py [fecha_s2 YYYY-MM-DD]   (por defecto 2026-02-28)
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.warp import reproject
from rasterio.windows import from_bounds

AQUI = Path(__file__).parent
SALIDA = AQUI.parent / "datos"
RES_MDT = 5      # m
LADO_S2 = 16     # km
PERFIL = dict(driver="GTiff", compress="deflate", tiled=True, blockxsize=256, blockysize=256)

minas = gpd.read_file(SALIDA / "taller1_uy.gpkg", layer="minas")

# --- MDT ---------------------------------------------------------------------------------------
xmin, ymin, xmax, ymax = minas.to_crs(5382).buffer(1000).total_bounds
xmin, ymin = np.floor([xmin / RES_MDT, ymin / RES_MDT]) * RES_MDT
xmax, ymax = np.ceil([xmax / RES_MDT, ymax / RES_MDT]) * RES_MDT
p = dict(service="WFS", version="2.0.0", request="GetFeature", typeNames="ortofotos:grilla_nacional_mdt",
         outputFormat="application/json", srsName="EPSG:5382", BBOX=f"{xmin},{ymin},{xmax},{ymax},EPSG:5382")
r = requests.get("https://mapas.ide.uy/geoserver-raster/ortofotos/wfs", params=p, timeout=120)
r.raise_for_status()
hojas = gpd.read_file(r.content)
print(len(hojas), "hojas del MDT:", hojas.nombre.tolist())
srcs = [rasterio.open("/vsicurl/" + u) for u in hojas.mdt_geot]
nodata = srcs[0].nodata
mdt, tr = merge(srcs, bounds=(xmin, ymin, xmax, ymax), res=RES_MDT, nodata=nodata,
                resampling=Resampling.average)
for s in srcs:
    s.close()
mdt = np.where(mdt[0] == nodata, np.nan, mdt[0]).astype("float32")
with rasterio.open(SALIDA / "mdt_minas.tif", "w", height=mdt.shape[0], width=mdt.shape[1], count=1,
                   dtype="float32", crs=5382, transform=tr, nodata=np.nan, predictor=3, **PERFIL) as f:
    f.write(mdt, 1)
    f.set_band_description(1, "altitud (m)")
print("MDT", mdt.shape, "altitud (m):", np.nanpercentile(mdt, [0, 50, 100]).round(1))

# --- Sentinel-2 --------------------------------------------------------------------------------
# Minas cae en la franja de superposición de los tiles 21HXB y 21HXC: ninguno cubre solo el
# cuadrado, así que se hace un mosaico de los dos tiles de la misma fecha (misma pasada y misma
# grilla UTM). En Earth Search v1 el offset de reflectancia ya viene aplicado
# (earthsearch:boa_offset_applied): reflectancia = valor / 10000.
FECHA_S2 = sys.argv[1] if len(sys.argv) > 1 else "2026-02-28"  # fin del verano, 0,1 % de nubes
c = minas.to_crs(32721).union_all().centroid
mitad = LADO_S2 * 500
caja = (c.x - mitad, c.y - mitad, c.x + mitad, c.y + mitad)
lon, lat = minas.union_all().centroid.coords[0]
busqueda = {"collections": ["sentinel-2-l2a"], "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "datetime": f"{FECHA_S2}T00:00:00Z/{FECHA_S2}T23:59:59Z", "limit": 10}
r = requests.post("https://earth-search.aws.element84.com/v1/search", json=busqueda, timeout=120)
r.raise_for_status()
escenas = r.json()["features"]
for e in escenas:
    pr = e["properties"]
    print(e["id"], f"nubes {pr['eo:cloud_cover']:.2f} %", "offset aplicado:", pr.get("earthsearch:boa_offset_applied"))
    assert pr.get("earthsearch:boa_offset_applied"), "sin offset aplicado: restar 1000 antes de guardar"

s2 = None
for e in escenas:
    bandas = []
    for b in ["blue", "green", "red", "nir"]:
        with rasterio.open(e["assets"][b]["href"]) as src:
            assert src.crs.to_epsg() == 32721, src.crs
            ventana = from_bounds(*caja, transform=src.transform)
            bandas.append(src.read(1, window=ventana, boundless=True, fill_value=0))
            tr_s2 = src.window_transform(ventana)
    tile = np.stack(bandas)
    s2 = tile if s2 is None else np.where(s2 == 0, tile, s2)
print("Píxeles sin dato en el mosaico:", f"{(s2 == 0).any(axis=0).mean():.2%}")
assert (s2 == 0).any(axis=0).mean() < 0.001

with rasterio.open(SALIDA / "sentinel2_minas.tif", "w", height=s2.shape[1], width=s2.shape[2], count=4,
                   dtype="uint16", crs=32721, transform=tr_s2, nodata=0, predictor=2, **PERFIL) as f:
    f.write(s2)
    for i, d in enumerate(["B02 azul", "B03 verde", "B04 rojo", "B08 infrarrojo cercano"], 1):
        f.set_band_description(i, d)
    f.update_tags(escenas=", ".join(e["id"] for e in escenas), fecha=FECHA_S2,
                  fuente="Copernicus Sentinel-2 L2A via Earth Search (AWS)")
ndvi = (s2[3].astype(float) - s2[2]) / (s2[3].astype(float) + s2[2])
print("S2", s2.shape, "NDVI p5/p50/p95:", np.nanpercentile(ndvi, [5, 50, 95]).round(2))

for f in sorted(SALIDA.glob("*.tif")):
    print(f"{f.name:30s} {f.stat().st_size / 1e6:6.2f} MB")
