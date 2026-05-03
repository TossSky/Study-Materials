"""
Lab 4 — задача о максимальном потоке в сети.

По описанию формата (в `job_Var1.in` после '****'):
  Первая строка: N variant
    variant = 1 — алгоритм Эдмондса-Карпа (BFS-аугментирующие пути)
    variant = 2 — алгоритм Диница (BFS-уровни + DFS-блокирующий поток)
  Однако в эталонных файлах Dinic.in/EdmKarp.in значение поля variant равно 1,
  и алгоритм фактически определяется именем файла. Поэтому реализуем оба
  алгоритма; алгоритм можно явно задать аргументом командной строки.

  Далее N строк по N токенов — матрица пропускных способностей.
  '*' означает отсутствие дуги, '0' стоит на диагонали.

Источники: вершины с нулевой суммарной входящей мощностью.
Стоки:     вершины с нулевой суммарной исходящей мощностью.
При нескольких источниках/стоках вводятся фиктивный супер-источник
и супер-сток с дугами бесконечной пропускной способности.

Формат выхода:
  1) номера источников через пробел;
  2) номера стоков через пробел;
  3) последовательность величин потока на итерациях алгоритма (через ", ");
  4) N×N матрица итогового потока (разделитель пробел);
  5) величина максимального потока.
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path


def parse_input(path: Path) -> tuple[int, int, list[list[str]]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1251")

    tokens_per_line: list[list[str]] = []
    for line in text.splitlines():
        if line.strip().startswith("*" * 10):
            break
        if line.strip():
            tokens_per_line.append(line.split())

    header = tokens_per_line[0]
    n = int(header[0])
    variant = int(header[1])
    matrix = [tokens_per_line[i + 1][:n] for i in range(n)]
    return n, variant, matrix


def edmonds_karp(cap: list[list[int]], src: int, snk: int):
    """Аугментирующие пути через BFS. Возвращает (max_flow, [pushes...], flow)."""
    size = len(cap)
    flow = [[0] * size for _ in range(size)]
    pushes: list[int] = []

    while True:
        parent = [-1] * size
        parent[src] = src
        q: deque[int] = deque([src])
        reached = False
        while q and not reached:
            u = q.popleft()
            for v in range(size):
                if parent[v] == -1 and cap[u][v] - flow[u][v] > 0:
                    parent[v] = u
                    if v == snk:
                        reached = True
                        break
                    q.append(v)
        if not reached:
            break

        push = 1 << 62
        v = snk
        while v != src:
            u = parent[v]
            push = min(push, cap[u][v] - flow[u][v])
            v = u

        v = snk
        while v != src:
            u = parent[v]
            flow[u][v] += push
            flow[v][u] -= push
            v = u
        pushes.append(push)

    return sum(pushes), pushes, flow


def dinic(cap: list[list[int]], src: int, snk: int):
    """Алгоритм Диница: BFS-уровни + DFS-блокирующий поток.
    Возвращает (max_flow, [phase_blocking_flows...], flow)."""
    size = len(cap)
    flow = [[0] * size for _ in range(size)]
    phases: list[int] = []

    def build_levels() -> list[int] | None:
        level = [-1] * size
        level[src] = 0
        q: deque[int] = deque([src])
        while q:
            u = q.popleft()
            for v in range(size):
                if level[v] == -1 and cap[u][v] - flow[u][v] > 0:
                    level[v] = level[u] + 1
                    q.append(v)
        return level if level[snk] != -1 else None

    def dfs(u: int, pushed: int, level: list[int], it: list[int]) -> int:
        if u == snk:
            return pushed
        while it[u] < size:
            v = it[u]
            if level[v] == level[u] + 1 and cap[u][v] - flow[u][v] > 0:
                d = dfs(v, min(pushed, cap[u][v] - flow[u][v]), level, it)
                if d > 0:
                    flow[u][v] += d
                    flow[v][u] -= d
                    return d
            it[u] += 1
        return 0

    INF = 1 << 62
    while True:
        level = build_levels()
        if level is None:
            break
        it = [0] * size
        phase = 0
        while True:
            d = dfs(src, INF, level, it)
            if d == 0:
                break
            phase += d
        if phase == 0:
            break
        phases.append(phase)

    return sum(phases), phases, flow


def solve_file(in_path: Path, out_path: Path, force_algo: str | None = None) -> dict:
    n, variant, matrix = parse_input(in_path)

    SUPER_SRC = 0
    SUPER_SNK = n + 1
    size = n + 2
    cap = [[0] * size for _ in range(size)]

    for i in range(n):
        for j in range(n):
            cell = matrix[i][j]
            if cell == "*":
                continue
            value = int(cell)
            if i == j:
                continue
            if value > 0:
                cap[i + 1][j + 1] = value

    out_total = [0] * (n + 1)
    in_total = [0] * (n + 1)
    for u in range(1, n + 1):
        for v in range(1, n + 1):
            c = cap[u][v]
            if c > 0:
                out_total[u] += c
                in_total[v] += c

    sources = [v for v in range(1, n + 1) if in_total[v] == 0 and out_total[v] > 0]
    sinks = [v for v in range(1, n + 1) if out_total[v] == 0 and in_total[v] > 0]
    if not sources or not sinks:
        raise RuntimeError("Не удалось определить источник/сток по балансу")

    INF_CAP = 1 << 60
    if len(sources) == 1 and len(sinks) == 1:
        src, snk = sources[0], sinks[0]
    else:
        for s in sources:
            cap[SUPER_SRC][s] = INF_CAP
        for t in sinks:
            cap[t][SUPER_SNK] = INF_CAP
        src, snk = SUPER_SRC, SUPER_SNK

    chosen = force_algo if force_algo else ("ek" if variant == 1 else "dinic")
    if chosen == "ek":
        algo = "Edmonds-Karp"
        total, iters, flow = edmonds_karp(cap, src, snk)
    elif chosen == "dinic":
        algo = "Dinic"
        total, iters, flow = dinic(cap, src, snk)
    else:
        raise ValueError(f"Неизвестный алгоритм: {chosen}")

    lines: list[str] = []
    lines.append(" ".join(str(v) for v in sources) + " ")
    lines.append(" ".join(str(v) for v in sinks) + " ")
    lines.append(", ".join(str(x) for x in iters))
    for u in range(1, n + 1):
        row = [str(max(flow[u][v], 0)) for v in range(1, n + 1)]
        lines.append(" ".join(row) + " ")
    lines.append(str(total))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "n": n,
        "variant": variant,
        "algo": algo,
        "sources": sources,
        "sinks": sinks,
        "iters": iters,
        "max_flow": total,
    }


def main() -> None:
    here = Path(__file__).parent
    if len(sys.argv) >= 3:
        force = sys.argv[3] if len(sys.argv) >= 4 else None
        info = solve_file(Path(sys.argv[1]), Path(sys.argv[2]), force)
        print(info)
        return

    targets = [
        (here / "Dinic.in", here / "Dinic.check.out", "dinic"),
        (here / "EdmKarp.in", here / "EdmKarp.check.out", "ek"),
        (here / "job_Var1.in", here / "job_Var1.out", None),
    ]
    for in_p, out_p, force in targets:
        if not in_p.exists():
            continue
        info = solve_file(in_p, out_p, force)
        print(
            f"{in_p.name}: N={info['n']}, var={info['variant']} ({info['algo']}), "
            f"sources={info['sources']}, sinks={info['sinks']}, "
            f"iters={info['iters']}, max_flow={info['max_flow']}  ->  {out_p.name}"
        )


if __name__ == "__main__":
    main()
