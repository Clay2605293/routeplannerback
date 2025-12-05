# build_services_voronoi.py
"""
Construye celdas Voronoi FINITAS para todos los servicios de OSM
y las guarda en app/data/services_voronoi.json.

Usa el patrón clásico voronoi_finite_polygons_2d para cerrar las
regiones infinitas con un "bounding circle" grande.
"""

from pathlib import Path
import json

import numpy as np
from scipy.spatial import Voronoi

from app.services.loader import load_osm_services

# Ruta al archivo de salida
BASE_DIR = Path(__file__).resolve().parent
DATA_VORONOI = BASE_DIR / "app" / "data" / "services_voronoi.json"


def voronoi_finite_polygons_2d(vor: Voronoi, radius: float | None = None):
    """
    Convertir regiones Voronoi 2D (posiblemente infinitas) en
    polígonos finitos, extendiendo los rayos hasta un círculo de radio dado.

    Basado en el ejemplo oficial de SciPy.
    """
    if vor.points.shape[1] != 2:
        raise ValueError("Solo soporta Voronoi 2D")

    new_regions: list[list[int]] = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        # ANTES: radius = vor.points.ptp().max() * 2.0
        radius = np.ptp(vor.points, axis=0).max() * 2.0

    # Mapa: índice de punto -> lista de (p2, v1, v2) para cada ridge
    all_ridges: dict[int, list[tuple[int, int, int]]] = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices, strict=False):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    # Recorremos cada región asociada a cada punto
    for p1, region_index in enumerate(vor.point_region):
        vertices = vor.regions[region_index]

        # Región vacía
        if len(vertices) == 0:
            new_regions.append([])
            continue

        # Si todos los vértices son válidos (>= 0), es región finita
        if all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue

        # Región infinita: reconstruirla
        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            # Si ambos vértices son válidos, no toca extender
            if v1 >= 0 and v2 >= 0:
                continue

            # Uno de los vértices es -1 → ridge infinito
            v_inf = v1 if v1 < 0 else v2
            v_fin = v2 if v1 < 0 else v1

            # Dirección del segmento entre los dos puntos que separa el ridge
            t = vor.points[p2] - vor.points[p1]
            t /= np.linalg.norm(t)

            # Vector normal al ridge
            n = np.array([-t[1], t[0]])

            # Punto "medio" en el vértice finito
            midpoint = vor.vertices[v_fin]

            # Elegimos el sentido de la normal que apunte hacia afuera
            direction = np.sign(np.dot(midpoint - center, n)) * n

            # Nuevo vértice extendido
            new_vertex = midpoint + direction * radius
            new_vertices.append(new_vertex.tolist())
            v_new = len(new_vertices) - 1

            new_region.append(v_new)

        # Ordenar los vértices de la región resultante
        vs = np.array([new_vertices[v] for v in new_region])
        centroid = vs.mean(axis=0)
        angles = np.arctan2(vs[:, 1] - centroid[1], vs[:, 0] - centroid[0])
        new_region = [v for _, v in sorted(zip(angles, new_region), key=lambda x: x[0])]

        new_regions.append(new_region)

    return new_regions, np.asarray(new_vertices)


def main():
    # Cargamos todos los servicios desde app/data/services_osm.json
    services = load_osm_services()
    if not services:
        raise RuntimeError("No hay servicios en services_osm.json")

    # points: (x = lon, y = lat)
    points = np.array(
        [[float(s["lon"]), float(s["lat"])] for s in services],
        dtype=float,
    )

    vor = Voronoi(points)

    # Convertimos todas las regiones a polígonos finitos
    regions, vertices = voronoi_finite_polygons_2d(vor, radius=None)

    cells: list[dict[str, object]] = []

    for svc, region in zip(services, regions, strict=False):
        if not region:
            continue

        polygon = []
        for v_idx in region:
            vx, vy = vertices[v_idx]
            # Recordar: x = lon, y = lat
            polygon.append(
                {
                    "lat": float(vy),
                    "lon": float(vx),
                }
            )

        cell = {
            "id": str(svc["id"]),
            "osm_id": int(svc["osm_id"]),
            "osm_type": str(svc["osm_type"]),
            "type": svc["type"],
            "name": svc["name"],
            "lat": float(svc["lat"]),
            "lon": float(svc["lon"]),
            "polygon": polygon,
        }
        cells.append(cell)

    DATA_VORONOI.parent.mkdir(parents=True, exist_ok=True)
    with DATA_VORONOI.open("w", encoding="utf-8") as f:
        json.dump(cells, f, ensure_ascii=False, indent=2)

    print(f"Voronoi guardado en {DATA_VORONOI} con {len(cells)} celdas.")


if __name__ == "__main__":
    main()
