"""Genera las figuras del grafo de juguete del Taller 2 ("¿Cómo funciona el algoritmo?").

Salidas en ../img/:
- grafo_juguete_1.png : cinco lugares de Minas, pesos en cuadras y el camino más corto Terminal → Parque
- grafo_juguete_2.png : lo mismo, con una obra en la calle Estadio–Plaza (5 cuadras en vez de 1)

Uso: python 04_grafo_juguete.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

AQUI = Path(__file__).parent
SALIDA = AQUI.parent / "img"
SALIDA.mkdir(exist_ok=True)

J = nx.Graph()
J.add_edge("Terminal", "Plaza", cuadras=4)
J.add_edge("Terminal", "Estadio", cuadras=2)
J.add_edge("Estadio", "Plaza", cuadras=1)
J.add_edge("Plaza", "Teatro", cuadras=5)
J.add_edge("Estadio", "Teatro", cuadras=8)
J.add_edge("Teatro", "Parque", cuadras=3)
J.add_edge("Plaza", "Parque", cuadras=10)

# posición de cada lugar en el dibujo (no son coordenadas reales)
posiciones = {"Terminal": (0, 2), "Estadio": (1, 0), "Plaza": (2, 2), "Teatro": (4, 1), "Parque": (5, 2.5)}


def dibujar(J, archivo, titulo):
    camino = nx.dijkstra_path(J, "Terminal", "Parque", weight="cuadras")
    costo = nx.dijkstra_path_length(J, "Terminal", "Parque", weight="cuadras")
    tramos = list(zip(camino[:-1], camino[1:]))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    nx.draw_networkx_edges(J, posiciones, ax=ax, edge_color="grey")
    nx.draw_networkx_edges(J, posiciones, ax=ax, edgelist=tramos, edge_color="red", width=4)
    nx.draw_networkx_nodes(J, posiciones, ax=ax, node_color="lightblue", node_size=1500)
    nx.draw_networkx_labels(J, posiciones, ax=ax, font_size=9)
    nx.draw_networkx_edge_labels(J, posiciones, ax=ax, edge_labels=nx.get_edge_attributes(J, "cuadras"))
    ax.set_title(f"{titulo}\n{' → '.join(camino)}: {costo} cuadras")
    ax.axis("off")
    fig.savefig(SALIDA / archivo, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(archivo, camino, costo)


dibujar(J, "grafo_juguete_1.png", "Camino más corto de la Terminal al Parque")
J.edges["Estadio", "Plaza"]["cuadras"] = 5
dibujar(J, "grafo_juguete_2.png", "Con una obra entre el Estadio y la Plaza (5 cuadras)")
