"""Prepara los grafos de calles de Minas para el Taller 2 (respaldo de Overpass).

Salidas en ../datos/:
- grafo_minas_drive.graphml : red para autos ("drive") de Minas, Lavalleja, Uruguay
- grafo_minas_walk.graphml  : red peatonal ("walk") de Minas, Lavalleja, Uruguay

Son los mismos grafos que el notebook descarga con ox.graph_from_place(); en el taller se usan solo
si la descarga desde OpenStreetMap falla o tarda demasiado (celdas de rescate).
Datos (c) colaboradores de OpenStreetMap, licencia ODbL.
Uso: python 03_grafos.py
"""
from pathlib import Path

import osmnx as ox

AQUI = Path(__file__).parent
SALIDA = AQUI.parent / "datos"
SALIDA.mkdir(exist_ok=True)
ox.settings.cache_folder = AQUI / "cache"

LUGAR = "Minas, Lavalleja, Uruguay"

for red in ["drive", "walk"]:
    G = ox.graph_from_place(LUGAR, network_type=red)
    archivo = SALIDA / f"grafo_minas_{red}.graphml"
    ox.save_graphml(G, archivo)
    print(f"{red}: {len(G.nodes)} nodos, {len(G.edges)} aristas -> {archivo.name} "
          f"({archivo.stat().st_size / 1e6:.1f} MB)")
