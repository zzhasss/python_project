"""
Реализация алгоритмов проекта «Алгоритмы в действии» с записью шагов (trace)
и подсчётом элементарных операций.

Каждый алгоритм принимает объект Tracer. Если tracer.record = True, то
каждый шаг сохраняется в tracer.steps — именно этот формат будет
отдавать Flask-сервер фронтенду для пошаговой визуализации.
Если record = False — считаются только счётчики (для бенчмарков).
"""
from collections import deque


class Tracer:
    def __init__(self, record=True):
        self.record = record
        self.steps = []
        self.comparisons = 0   # сравнения элементов
        self.swaps = 0         # обмены (bubble, quick)
        self.writes = 0        # записи в массив (insertion)
        self.max_depth = 0     # макс. глубина стека (quick sort)

    def add(self, **step):
        if self.record:
            step["step"] = len(self.steps)
            self.steps.append(step)

    def stats(self):
        return {
            "comparisons": self.comparisons,
            "swaps": self.swaps,
            "writes": self.writes,
            "max_depth": self.max_depth,
            "steps": len(self.steps),
        }


# --------------------------------------------------------------------------
# ПОИСК
# --------------------------------------------------------------------------
def linear_search(arr, target, t: Tracer):
    for i, x in enumerate(arr):
        t.comparisons += 1
        found = x == target
        t.add(type="compare", index=i, value=x, target=target, found=found)
        if found:
            t.add(type="found", index=i)
            return i
    t.add(type="not_found")
    return -1


def binary_search(arr, target, t: Tracer):
    """arr должен быть отсортирован по возрастанию."""
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        t.comparisons += 1
        t.add(type="compare", low=low, high=high, mid=mid,
              value=arr[mid], target=target, range_size=high - low + 1)
        if arr[mid] == target:
            t.add(type="found", index=mid)
            return mid
        if arr[mid] < target:
            low = mid + 1
            t.add(type="go_right", low=low, high=high)
        else:
            high = mid - 1
            t.add(type="go_left", low=low, high=high)
    t.add(type="not_found")
    return -1


# --------------------------------------------------------------------------
# СОРТИРОВКИ
# --------------------------------------------------------------------------
def bubble_sort(arr, t: Tracer):
    a = list(arr)
    n = len(a)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            t.comparisons += 1
            t.add(type="compare", indices=[j, j + 1], array=a[:] if t.record else None)
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                t.swaps += 1
                swapped = True
                t.add(type="swap", indices=[j, j + 1], array=a[:] if t.record else None)
        t.add(type="mark_sorted", index=n - 1 - i)
        if not swapped:
            break
    t.add(type="done", array=a[:] if t.record else None)
    return a


def insertion_sort(arr, t: Tracer):
    a = list(arr)
    for i in range(1, len(a)):
        key = a[i]
        t.add(type="select_key", index=i, key=key, array=a[:] if t.record else None)
        j = i - 1
        while j >= 0:
            t.comparisons += 1
            t.add(type="compare", indices=[j, i], key=key)
            if a[j] > key:
                a[j + 1] = a[j]
                t.writes += 1
                t.add(type="shift", from_index=j, to_index=j + 1,
                      array=a[:] if t.record else None)
                j -= 1
            else:
                break
        a[j + 1] = key
        t.writes += 1
        t.add(type="insert", index=j + 1, key=key, array=a[:] if t.record else None)
    t.add(type="done", array=a[:] if t.record else None)
    return a


def quick_sort(arr, t: Tracer):
    """Быстрая сортировка, разбиение Ломуто, опорный — последний элемент.
    Реализована итеративно (явный стек), чтобы не упираться в лимит рекурсии
    на худшем случае (отсортированный массив)."""
    a = list(arr)
    stack = [(0, len(a) - 1)]
    while stack:
        t.max_depth = max(t.max_depth, len(stack))
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        pivot = a[hi]
        t.add(type="pivot", index=hi, value=pivot, lo=lo, hi=hi)
        i = lo
        for j in range(lo, hi):
            t.comparisons += 1
            t.add(type="compare", indices=[j, hi])
            if a[j] < pivot:
                if i != j:
                    a[i], a[j] = a[j], a[i]
                    t.swaps += 1
                    t.add(type="swap", indices=[i, j], array=a[:] if t.record else None)
                i += 1
        if i != hi:
            a[i], a[hi] = a[hi], a[i]
            t.swaps += 1
            t.add(type="swap", indices=[i, hi], array=a[:] if t.record else None)
        t.add(type="pivot_placed", index=i, array=a[:] if t.record else None)
        stack.append((i + 1, hi))
        stack.append((lo, i - 1))
    t.add(type="done", array=a[:] if t.record else None)
    return a


SORTS = {
    "bubble_sort": bubble_sort,
    "insertion_sort": insertion_sort,
    "quick_sort": quick_sort,
}


# --------------------------------------------------------------------------
# ГРАФЫ
# --------------------------------------------------------------------------
def adjacency(graph):
    adj = {node["id"]: [] for node in graph["nodes"]}
    for u, v in graph["edges"]:
        adj[u].append(v)
        if not graph.get("directed", False):
            adj[v].append(u)
    for k in adj:
        adj[k].sort()
    return adj


def bfs(graph, start, t: Tracer):
    adj = adjacency(graph)
    visited = {start}
    order = []
    level = {start: 0}
    q = deque([start])
    edges_examined = 0
    max_frontier = 1
    t.add(type="enqueue", node=start, parent=None, queue=list(q))
    while q:
        u = q.popleft()
        order.append(u)
        t.add(type="dequeue", node=u, level=level[u], queue=list(q) if t.record else None,
              visited=order[:] if t.record else None)
        for v in adj[u]:
            edges_examined += 1
            if v not in visited:
                visited.add(v)
                level[v] = level[u] + 1
                q.append(v)
                t.add(type="tree_edge", edge=[u, v], queue=list(q) if t.record else None)
            else:
                t.add(type="skip_edge", edge=[u, v])
        max_frontier = max(max_frontier, len(q))
    t.add(type="done", order=order if t.record else None)
    return {
        "order": order,
        "visited": len(order),
        "edges_examined": edges_examined,
        "max_frontier": max_frontier,
        "depth": max(level.values()),
    }


def dfs(graph, start, t: Tracer):
    """Итеративный DFS; соседи кладутся в стек в обратном порядке,
    чтобы порядок обхода совпадал с рекурсивной версией."""
    adj = adjacency(graph)
    visited = set()
    order = []
    depth = {start: 0}
    stack = [(start, None)]
    edges_examined = 0
    max_frontier = 1
    t.add(type="push", node=start, parent=None, stack=[start])
    while stack:
        u, parent = stack.pop()
        if u in visited:
            t.add(type="skip_node", node=u)
            continue
        visited.add(u)
        order.append(u)
        t.add(type="visit", node=u, parent=parent,
              stack=[s for s, _ in stack] if t.record else None,
              visited=order[:] if t.record else None)
        for v in reversed(adj[u]):
            edges_examined += 1
            if v not in visited:
                depth[v] = depth[u] + 1 if v not in depth else min(depth[v], depth[u] + 1)
                stack.append((v, u))
                t.add(type="push", node=v, parent=u)
        max_frontier = max(max_frontier, len(stack))
    t.add(type="done", order=order if t.record else None)
    return {
        "order": order,
        "visited": len(order),
        "edges_examined": edges_examined,
        "max_frontier": max_frontier,
        "depth": None,
    }


GRAPH_ALGOS = {"bfs": bfs, "dfs": dfs}
