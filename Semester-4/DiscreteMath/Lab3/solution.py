"""
Lab 3, вариант 8 — задача об узких местах (bottleneck / max-min paths).

Вход: матрица смежности N×N, источник s.
Алгоритм: модифицированная Дейкстра.
  D[v] = максимально возможное минимальное ребро на пути s → v
  Рекуррентность:  D[v] := max(D[v], min(D[u], w(u,v)))
  Итерация: на каждом шаге выбирается необработанная вершина u с максимальным D[u],
  из неё релаксируются исходящие рёбра.

Выход: на каждом шаге печатается D и P (массив предков).
  *  — позиция источника
  -  — вершина ещё недостижима
"""

import sys
import os
from pathlib import Path


def parse_input(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        tokens_per_line = []
        for line in f:
            # разделитель комментариев — строка из звёздочек
            if line.strip().startswith("*" * 10):
                break
            tokens_per_line.append(line.split())
    header = tokens_per_line[0]
    n = int(header[0])
    variant = int(header[1])
    source = int(header[2])
    matrix = []
    for i in range(1, n + 1):
        row = tokens_per_line[i][:n]
        matrix.append(row)
    return n, variant, source, matrix


def solve(n: int, source: int, matrix: list[list[str]]):
    NEG = None  # обозначаем -∞ как None для наглядности
    POS = "INF"  # +∞ для источника

    D = [NEG] * (n + 1)      # 1-индексация
    P = [source] * (n + 1)
    processed = [False] * (n + 1)

    D[source] = POS
    processed[source] = True

    # --- шаг 1: инициализация, релаксация из источника ---
    for j in range(1, n + 1):
        if j == source:
            continue
        cell = matrix[source - 1][j - 1]
        if cell == "*":
            continue
        w = int(cell)
        D[j] = w
        P[j] = source

    steps = [snapshot(D, P, n)]

    # --- следующие шаги: на каждом выбираем необработанную вершину с max D ---
    # Снимок добавляем только если после релаксации ещё остались необработанные
    # достижимые вершины (иначе последний снимок был бы дубликатом).
    while True:
        best_v = -1
        best_d = None
        for v in range(1, n + 1):
            if processed[v] or D[v] is None:
                continue
            if best_d is None or D[v] > best_d:
                best_d = D[v]
                best_v = v
        if best_v == -1:
            break
        processed[best_v] = True
        # релаксация исходящих дуг из best_v
        for j in range(1, n + 1):
            if processed[j]:
                continue
            cell = matrix[best_v - 1][j - 1]
            if cell == "*":
                continue
            w = int(cell)
            d_u = float("inf") if D[best_v] == POS else D[best_v]
            new_d = min(d_u, w)
            if D[j] is None or new_d > D[j]:
                D[j] = new_d
                P[j] = best_v
        # есть ли ещё необработанные достижимые?
        has_more = any(
            not processed[v] and D[v] is not None for v in range(1, n + 1)
        )
        new_snap = snapshot(D, P, n)
        # пропускаем снимок если он дублирует предыдущий (итерация ничего не
        # изменила — например, обработана "тупиковая" вершина)
        if new_snap != steps[-1]:
            steps.append(new_snap)
        if not has_more:
            break

    return steps


def snapshot(D, P, n):
    return ([D[i] for i in range(1, n + 1)], [P[i] for i in range(1, n + 1)])


def format_output(steps, source: int, n: int) -> str:
    out_lines = []
    for idx, (D_row, P_row) in enumerate(steps, start=1):
        out_lines.append(str(idx))
        d_tokens = []
        for j in range(1, n + 1):
            v = D_row[j - 1]
            if j == source:
                d_tokens.append("*")
            elif v is None:
                d_tokens.append("-")
            elif v == "INF":
                d_tokens.append("*")
            else:
                d_tokens.append(str(v))
        p_tokens = [str(P_row[j - 1]) for j in range(1, n + 1)]
        out_lines.append("D: " + " ".join(d_tokens) + " ")
        out_lines.append("P: " + " ".join(p_tokens) + " ")
    return "\n".join(out_lines) + "\n"


def main(in_path: str, out_path: str):
    n, variant, source, matrix = parse_input(Path(in_path))
    assert variant == 5, f"Ожидался вариант 5 (матрица), получен {variant}"
    steps = solve(n, source, matrix)
    out = format_output(steps, source, n)
    Path(out_path).write_text(out, encoding="utf-8")
    print(f"{in_path}: N={n}, source={source}, шагов={len(steps)}  ->  {out_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    if len(sys.argv) >= 3:
        main(sys.argv[1], sys.argv[2])
    else:
        # По умолчанию: решить моё задание и проверить пример
        main(str(here / "MaxMin.in"), str(here / "MaxMin.check.out"))
        main(str(here / "job_Var8.in"), str(here / "job_Var8.out"))
