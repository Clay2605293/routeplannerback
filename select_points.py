# select_points.py
import random
from typing import List, Tuple, Dict
from geopy.distance import distance as geo_distance

from app.graph.loader import load_graph

# Parámetros de las categorías (en metros)
SHORT_MAX = 1000.0          # < 1000 m
MID_MIN = 1000.0            # >= 1000 m
MID_MAX = 5000.0            # <= 5000 m
LONG_MIN = 5000.0           # > 5000 m

NUM_PER_BUCKET = 5          # parejas por categoría
MAX_TRIES = 50000           # límite de intentos aleatorios para no ciclarse


def compute_dist_m(node_a_data: dict, node_b_data: dict) -> float:
    """Distancia geodésica en metros entre dos nodos (lat/lon)."""
    lat_a, lon_a = node_a_data["y"], node_a_data["x"]
    lat_b, lon_b = node_b_data["y"], node_b_data["x"]
    return geo_distance((lat_a, lon_a), (lat_b, lon_b)).m


def main():
    print("Cargando grafo con load_graph()...")
    G, _ = load_graph()
    nodes: List[Tuple[int, dict]] = list(G.nodes(data=True))
    print(f"Nodos totales en el grafo: {len(nodes)}")

    # Buckets para las parejas
    short_pairs: List[Tuple[int, dict, int, dict, float]] = []
    mid_pairs: List[Tuple[int, dict, int, dict, float]] = []
    long_pairs: List[Tuple[int, dict, int, dict, float]] = []

    # Para evitar repetir la misma pareja (independiente del orden)
    seen_pairs = set()

    tries = 0
    while tries < MAX_TRIES:
        tries += 1

        # Si ya llenamos todo, rompemos
        if (len(short_pairs) >= NUM_PER_BUCKET and
            len(mid_pairs) >= NUM_PER_BUCKET and
            len(long_pairs) >= NUM_PER_BUCKET):
            break

        # Muestra dos nodos al azar
        (id_a, data_a) = random.choice(nodes)
        (id_b, data_b) = random.choice(nodes)

        if id_a == id_b:
            continue

        key = tuple(sorted((id_a, id_b)))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        d = compute_dist_m(data_a, data_b)

        # Clasifica según la distancia
        if d < SHORT_MAX and len(short_pairs) < NUM_PER_BUCKET:
            short_pairs.append((id_a, data_a, id_b, data_b, d))
        elif MID_MIN <= d <= MID_MAX and len(mid_pairs) < NUM_PER_BUCKET:
            mid_pairs.append((id_a, data_a, id_b, data_b, d))
        elif d > LONG_MIN and len(long_pairs) < NUM_PER_BUCKET:
            long_pairs.append((id_a, data_a, id_b, data_b, d))

    print()
    print("Intentos realizados:", tries)
    print(f"Short (< {SHORT_MAX} m): {len(short_pairs)} parejas")
    print(f"Medium ({MID_MIN}–{MID_MAX} m): {len(mid_pairs)} parejas")
    print(f"Long (> {LONG_MIN} m): {len(long_pairs)} parejas")
    print()

    def print_bucket(name: str, pairs: List[Tuple[int, dict, int, dict, float]]):
        print(f"=== {name} ===")
        for i, (id_a, data_a, id_b, data_b, d) in enumerate(sorted(pairs, key=lambda p: p[4])):
            lat_a, lon_a = data_a["y"], data_a["x"]
            lat_b, lon_b = data_b["y"], data_b["x"]
            print(f"Pair {i+1}:")
            print(f"  A: node_id={id_a}, lat={lat_a:.6f}, lon={lon_a:.6f}")
            print(f"  B: node_id={id_b}, lat={lat_b:.6f}, lon={lon_b:.6f}")
            print(f"  Distance: {d:.2f} m")
            print()
        print()

    print_bucket("Short (< 1000 m)", short_pairs)
    print_bucket("Medium (1000–5000 m)", mid_pairs)
    print_bucket("Long (> 5000 m)", long_pairs)

    # Construye lista de nodos únicos que aparecen en todas las parejas
    unique_nodes: Dict[int, Tuple[float, float]] = {}
    for pairs in (short_pairs, mid_pairs, long_pairs):
        for (id_a, data_a, id_b, data_b, d) in pairs:
            unique_nodes[id_a] = (data_a["y"], data_a["x"])
            unique_nodes[id_b] = (data_b["y"], data_b["x"])

    print("=== Coordenadas únicas de nodos usados en las parejas ===")
    unique_list = list(unique_nodes.items())
    print(f"Total nodos únicos: {len(unique_list)}")
    print("Primeros 20, para usar como puntos (lat, lon) del proyecto:")

    for idx, (node_id, (lat, lon)) in enumerate(unique_list[:20], start=1):
        print(f"{idx:2d}. node_id={node_id}, lat={lat:.6f}, lon={lon:.6f}")

    print()
    print("Puedes copiar estos 20 (o menos) puntos como coordenadas de entrada")
    print("para el Componente 1 (KD-tree vs búsqueda exhaustiva), y las parejas")
    print("clasificadas para el Componente 2 (rutas con diferentes distancias).")


if __name__ == "__main__":
    main()
