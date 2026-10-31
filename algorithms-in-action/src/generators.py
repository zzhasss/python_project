"""Генераторы входных данных: массивы разных типов и графы разных топологий."""
import math
import random

ARRAY_TYPES = ["random", "sorted", "reversed", "nearly_sorted", "few_unique"]


def make_array(kind, n, rng: random.Random, max_value=None):
    max_value = max_value or max(99, n * 10)
    if kind == "few_unique":
        values = rng.sample(range(1, max_value + 1), k=min(5, max_value))
        return [rng.choice(values) for _ in range(n)]
    base = [rng.randint(1, max_value) for _ in range(n)]
    if kind == "random":
        return base
    if kind == "sorted":
        return sorted(base)
    if kind == "reversed":
        return sorted(base, reverse=True)
    if kind == "nearly_sorted":
        a = sorted(base)
        for _ in range(max(1, n // 20)):          # ~5% случайных перестановок
            i, j = rng.randrange(n), rng.randrange(n)
            a[i], a[j] = a[j], a[i]
        return a
    raise ValueError(kind)


# --------------------------------------------------------------------------
# Раскладка вершин (координаты нужны фронтенду для отрисовки)
# --------------------------------------------------------------------------
def circle_layout(n, w=600, h=400):
    cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 30
    return [(round(cx + r * math.cos(2 * math.pi * i / n), 1),
             round(cy + r * math.sin(2 * math.pi * i / n), 1)) for i in range(n)]


def tree_layout(n, w=600, h=400):
    depth = int(math.log2(n)) + 1
    pos = []
    for i in range(n):
        level = int(math.log2(i + 1))
        idx = i + 1 - 2 ** level
        count = 2 ** level
        pos.append((round(w * (idx + 0.5) / count, 1),
                    round(30 + (h - 60) * level / max(1, depth - 1), 1)))
    return pos


def grid_layout(rows, cols, w=600, h=400):
    return [(round(30 + (w - 60) * c / max(1, cols - 1), 1),
             round(30 + (h - 60) * r / max(1, rows - 1), 1))
            for r in range(rows) for c in range(cols)]


def _graph(name, n, edges, layout, directed=False):
    return {
        "name": name,
        "directed": directed,
        "n_nodes": n,
        "n_edges": len(edges),
        "nodes": [{"id": i, "label": str(i), "x": x, "y": y} for i, (x, y) in enumerate(layout)],
        "edges": [list(e) for e in edges],
    }


# --------------------------------------------------------------------------
# Топологии графов
# --------------------------------------------------------------------------
def path_graph(n):
    return _graph("path", n, [(i, i + 1) for i in range(n - 1)], circle_layout(n))


def cycle_graph(n):
    return _graph("cycle", n, [(i, (i + 1) % n) for i in range(n)], circle_layout(n))


def star_graph(n):
    return _graph("star", n, [(0, i) for i in range(1, n)], circle_layout(n))


def complete_graph(n):
    return _graph("complete", n, [(i, j) for i in range(n) for j in range(i + 1, n)],
                  circle_layout(n))


def binary_tree(n):
    return _graph("binary_tree", n, [((i - 1) // 2, i) for i in range(1, n)], tree_layout(n))


def grid_graph(n):
    cols = max(2, int(round(math.sqrt(n))))
    rows = max(2, n // cols)
    edges = []
    for r in range(rows):
        for c in range(cols):
            v = r * cols + c
            if c + 1 < cols:
                edges.append((v, v + 1))
            if r + 1 < rows:
                edges.append((v, v + cols))
    return _graph("grid", rows * cols, edges, grid_layout(rows, cols))


def random_connected(n, avg_extra_degree, rng, name):
    """Случайное остовное дерево + дополнительные случайные рёбра."""
    perm = list(range(n))
    rng.shuffle(perm)
    edges = set()
    for i in range(1, n):
        u, v = perm[i], perm[rng.randrange(i)]
        edges.add((min(u, v), max(u, v)))
    target = len(edges) + int(n * avg_extra_degree / 2)
    max_edges = n * (n - 1) // 2
    while len(edges) < min(target, max_edges):
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            edges.add((min(u, v), max(u, v)))
    return _graph(name, n, sorted(edges), circle_layout(n))


def random_sparse(n, rng):
    return random_connected(n, 2, rng, "random_sparse")


def random_dense(n, rng):
    return random_connected(n, max(2, n // 5), rng, "random_dense")


def disconnected(n, rng):
    """Две компоненты связности: обход из вершины 0 не дойдёт до второй."""
    half = n // 2
    g1 = random_connected(half, 2, rng, "tmp")
    g2 = random_connected(n - half, 2, rng, "tmp")
    edges = g1["edges"] + [[u + half, v + half] for u, v in g2["edges"]]
    return _graph("disconnected", n, edges, circle_layout(n))


GRAPH_TYPES = {
    "path": lambda n, rng: path_graph(n),
    "cycle": lambda n, rng: cycle_graph(n),
    "star": lambda n, rng: star_graph(n),
    "complete": lambda n, rng: complete_graph(n),
    "binary_tree": lambda n, rng: binary_tree(n),
    "grid": lambda n, rng: grid_graph(n),
    "random_sparse": random_sparse,
    "random_dense": random_dense,
    "disconnected": disconnected,
}
