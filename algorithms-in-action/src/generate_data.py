"""
Генерация данных проекта «Алгоритмы в действии». Все данные сохраняются в CSV.

Запуск из корня репозитория:
    python src/generate_data.py

Генерация воспроизводима: используется фиксированный seed.
"""
import csv
import os
import random
import time

from algorithms import SORTS, GRAPH_ALGOS, Tracer, linear_search, binary_search
from generators import ARRAY_TYPES, GRAPH_TYPES, make_array

SEED = 42
REPEATS = 3
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def write_csv(name, rows, fields):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  data/{name}: {len(rows)} строк")


def seq(x):
    """Список -> строка через пробел (для хранения состояния массива/очереди в одной ячейке)."""
    return "" if x is None else " ".join(map(str, x))


# --------------------------------------------------------------------------
# 1. Входные данные: массивы и графы
# --------------------------------------------------------------------------
def gen_inputs():
    print("1) Входные данные")
    rng = random.Random(SEED)
    arrays, array_values = {}, []
    for kind in ARRAY_TYPES:
        for n in [8, 10, 15, 20, 50, 100]:
            arr = make_array(kind, n, rng, max_value=99)
            aid = f"{kind}_{n}"
            arrays[aid] = arr
            for pos, v in enumerate(arr):
                array_values.append({"array_id": aid, "array_type": kind, "size": n,
                                     "position": pos, "value": v})
    write_csv("arrays.csv", array_values, ["array_id", "array_type", "size", "position", "value"])

    graphs, g_rows, n_rows, e_rows = {}, [], [], []
    for gtype, make in GRAPH_TYPES.items():
        for n in [6, 10, 16]:
            g = make(n, rng)
            gid = f"{gtype}_{n}"
            graphs[gid] = g
            g_rows.append({"graph_id": gid, "graph_type": gtype, "directed": g["directed"],
                           "n_nodes": g["n_nodes"], "n_edges": g["n_edges"]})
            for node in g["nodes"]:
                n_rows.append({"graph_id": gid, "node_id": node["id"], "label": node["label"],
                               "x": node["x"], "y": node["y"]})
            for k, (u, v) in enumerate(g["edges"]):
                e_rows.append({"graph_id": gid, "edge_id": k, "source": u, "target": v})
    write_csv("graphs.csv", g_rows, ["graph_id", "graph_type", "directed", "n_nodes", "n_edges"])
    write_csv("graph_nodes.csv", n_rows, ["graph_id", "node_id", "label", "x", "y"])
    write_csv("graph_edges.csv", e_rows, ["graph_id", "edge_id", "source", "target"])
    return arrays, graphs


# --------------------------------------------------------------------------
# 2. Пошаговые трассы выполнения алгоритмов
# --------------------------------------------------------------------------
STEP_FIELDS = ["trace_id", "step", "step_type", "index_1", "index_2", "value", "target",
               "low", "high", "mid", "node", "parent", "edge_from", "edge_to",
               "level", "frontier_state", "visited_state", "array_state"]


def flatten_step(trace_id, s):
    idx = s.get("indices") or [s.get("index", s.get("from_index")), s.get("to_index")]
    edge = s.get("edge") or [None, None]
    return {
        "trace_id": trace_id, "step": s["step"], "step_type": s["type"],
        "index_1": idx[0], "index_2": idx[1] if len(idx) > 1 else None,
        "value": s.get("value", s.get("key")), "target": s.get("target"),
        "low": s.get("low", s.get("lo")), "high": s.get("high", s.get("hi")), "mid": s.get("mid"),
        "node": s.get("node"), "parent": s.get("parent"),
        "edge_from": edge[0], "edge_to": edge[1], "level": s.get("level"),
        "frontier_state": seq(s.get("queue", s.get("stack"))),
        "visited_state": seq(s.get("visited", s.get("order"))),
        "array_state": seq(s.get("array")),
    }


def gen_traces(arrays, graphs):
    print("2) Пошаговые трассы")
    meta, steps = [], []

    def save(trace_id, category, algorithm, input_id, t, result, target="", case=""):
        meta.append({"trace_id": trace_id, "category": category, "algorithm": algorithm,
                     "input_id": input_id, "target": target, "case": case,
                     "n_steps": len(t.steps), "comparisons": t.comparisons,
                     "swaps": t.swaps, "writes": t.writes, "result": result})
        steps.extend(flatten_step(trace_id, s) for s in t.steps)

    for kind in ARRAY_TYPES:
        aid = f"{kind}_10"
        for algo, fn in SORTS.items():
            t = Tracer()
            res = fn(arrays[aid], t)
            save(f"{algo}__{aid}", "sorting", algo, aid, t, seq(res))

    aid = "sorted_20"
    arr = arrays[aid]
    for case, target in {"first": arr[0], "middle": arr[10], "last": arr[-1], "absent": 100}.items():
        for algo, fn in [("linear_search", linear_search), ("binary_search", binary_search)]:
            t = Tracer()
            res = fn(arr, target, t)
            save(f"{algo}__{aid}__{case}", "search", algo, aid, t, res, target, case)

    for gtype in GRAPH_TYPES:
        gid = f"{gtype}_10"
        for algo, fn in GRAPH_ALGOS.items():
            t = Tracer()
            res = fn(graphs[gid], 0, t)
            save(f"{algo}__{gid}", "graph", algo, gid, t, seq(res["order"]))

    write_csv("traces.csv", meta, list(meta[0].keys()))
    write_csv("trace_steps.csv", steps, STEP_FIELDS)


# --------------------------------------------------------------------------
# 3. Замеры на больших входах (число операций и время)
# --------------------------------------------------------------------------
def timed(fn, *args):
    t = Tracer(record=False)
    start = time.perf_counter()
    res = fn(*args, t)
    return res, t, (time.perf_counter() - start) * 1000


def gen_sorting_runs():
    print("3) Запуски сортировок (~1-2 мин)")
    rows = []
    for kind in ARRAY_TYPES:
        for n in [10, 50, 100, 250, 500, 1000, 2000]:
            for run in range(REPEATS):
                seed = SEED * 1000 + n * 10 + run
                arr = make_array(kind, n, random.Random(seed))
                for algo, fn in SORTS.items():
                    res, t, ms = timed(fn, arr)
                    assert res == sorted(arr)
                    rows.append({"algorithm": algo, "input_type": kind, "n": n, "run": run,
                                 "seed": seed, "comparisons": t.comparisons, "swaps": t.swaps,
                                 "writes": t.writes,
                                 "max_stack_depth": t.max_depth if algo == "quick_sort" else "",
                                 "time_ms": round(ms, 4)})
    write_csv("sorting_runs.csv", rows, list(rows[0].keys()))


def gen_search_runs():
    print("4) Запуски поиска")
    rows = []
    rng = random.Random(SEED + 2)
    for n in [10, 100, 1000, 10_000, 100_000]:
        arr = sorted(rng.sample(range(1, n * 10), n))
        cases = {"first": [arr[0]], "middle": [arr[n // 2]], "last": [arr[-1]],
                 "absent": [n * 10 + 1], "random": [rng.choice(arr) for _ in range(50)]}
        for case, targets in cases.items():
            for q, target in enumerate(targets):
                for algo, fn in [("linear_search", linear_search), ("binary_search", binary_search)]:
                    idx, t, ms = timed(fn, arr, target)
                    rows.append({"algorithm": algo, "n": n, "case": case, "query": q,
                                 "target": target, "found_index": idx,
                                 "comparisons": t.comparisons, "time_ms": round(ms, 5)})
    write_csv("search_runs.csv", rows, list(rows[0].keys()))


def gen_graph_runs():
    print("5) Запуски обходов графа")
    rows = []
    for gtype, make in GRAPH_TYPES.items():
        for n in [10, 50, 100, 250, 500, 1000]:
            if gtype == "complete" and n > 500:
                continue
            for run in range(REPEATS):
                seed = SEED * 7 + n + run
                g = make(n, random.Random(seed))
                for algo, fn in GRAPH_ALGOS.items():
                    res, t, ms = timed(fn, g, 0)
                    rows.append({"algorithm": algo, "graph_type": gtype, "n_nodes": g["n_nodes"],
                                 "n_edges": g["n_edges"], "run": run, "seed": seed,
                                 "visited": res["visited"],
                                 "edges_examined": res["edges_examined"],
                                 "max_frontier": res["max_frontier"],
                                 "bfs_levels": res["depth"] if res["depth"] is not None else "",
                                 "time_ms": round(ms, 4)})
    write_csv("graph_runs.csv", rows, list(rows[0].keys()))


if __name__ == "__main__":
    arrays, graphs = gen_inputs()
    gen_traces(arrays, graphs)
    gen_sorting_runs()
    gen_search_runs()
    gen_graph_runs()
    print("Готово.")
