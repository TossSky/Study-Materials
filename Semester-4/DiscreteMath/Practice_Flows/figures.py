"""
Генератор рисунков к 9 задачам о потоках в сетях.
Каждый рисунок сохраняется в файл fig_NN.png с прозрачным белым фоном,
размер подобран под вставку в docx (ширина ~14 см при 150 dpi).
"""
import os
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle
import networkx as nx

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.linewidth': 0,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.08,
    'savefig.facecolor': 'white',
})

OUT = os.path.dirname(os.path.abspath(__file__))


def save(name):
    path = os.path.join(OUT, name)
    plt.savefig(path)
    plt.close()
    print(f'  -> {name}')


# ---------- Утилиты рисования сети --------------
def draw_arrow(ax, p1, p2, *, color='black', lw=1.6, shrink=14, style='-|>', zorder=2):
    arrow = FancyArrowPatch(
        p1, p2, arrowstyle=style, color=color, lw=lw,
        mutation_scale=16, shrinkA=shrink, shrinkB=shrink, zorder=zorder,
    )
    ax.add_patch(arrow)


def draw_node(ax, pos, label, *, r=0.28, face='white', edge='black', text_color='black', lw=1.8):
    c = Circle(pos, r, facecolor=face, edgecolor=edge, lw=lw, zorder=3)
    ax.add_patch(c)
    ax.text(pos[0], pos[1], label, ha='center', va='center',
            fontsize=12, fontweight='bold', color=text_color, zorder=4)


def edge_label(ax, p1, p2, text, *, offset=0.22, color='black', fontsize=10, italic=False):
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    # Перпендикулярное смещение
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy) or 1.0
    nx_, ny_ = -dy / L, dx / L
    tx, ty = mx + offset * nx_, my + offset * ny_
    ax.text(tx, ty, text, ha='center', va='center', color=color,
            fontsize=fontsize, fontstyle='italic' if italic else 'normal', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=1.2))


def base_ax(figsize=(9, 5)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect('equal')
    ax.set_axis_off()
    return fig, ax


# =============================================================
# Figure 1 — Разложение потока на пути и циклы (Задача 1, 2)
# =============================================================
def fig_decomposition():
    fig, ax = base_ax((11, 4.5))
    P = {
        's':  (0.0, 1.5),
        'a':  (2.0, 3.0),
        'b':  (2.0, 0.0),
        'c':  (4.0, 3.0),
        'd':  (4.0, 0.0),
        't':  (6.0, 1.5),
    }

    edges_path1 = [('s', 'a'), ('a', 'c'), ('c', 't')]   # путь 1
    edges_path2 = [('s', 'b'), ('b', 'd'), ('d', 't')]   # путь 2
    edges_cycle = [('a', 'b'), ('b', 'd'), ('d', 'c'), ('c', 'a')]  # цикл

    # Общая сеть (без подсветки)
    for u, v in edges_path1:
        draw_arrow(ax, P[u], P[v], color='#2E86DE', lw=2.0)
    for u, v in edges_path2:
        draw_arrow(ax, P[u], P[v], color='#10AC84', lw=2.0)
    # Цикл — пунктир
    for u, v in [('a', 'b'), ('c', 'a')]:
        draw_arrow(ax, P[u], P[v], color='#EE5253', lw=1.8, style='-|>')
    for u, v in [('d', 'c')]:
        draw_arrow(ax, P[u], P[v], color='#EE5253', lw=1.8, style='-|>')

    for name, p in P.items():
        if name in ('s', 't'):
            draw_node(ax, p, name, face='#fff3cd', edge='#b37400')
        else:
            draw_node(ax, p, name)

    # Легенда
    legend = [
        mpatches.Patch(color='#2E86DE', label='путь P₁: s → a → c → t'),
        mpatches.Patch(color='#10AC84', label='путь P₂: s → b → d → t'),
        mpatches.Patch(color='#EE5253', label='цикл C: a → b (уже в P₂) → d (уже в P₂) → c → a'),
    ]
    ax.legend(handles=legend, loc='lower center', bbox_to_anchor=(0.5, -0.05),
              frameon=False, fontsize=10, ncol=1)

    ax.set_xlim(-0.6, 6.6)
    ax.set_ylim(-1.3, 3.6)
    ax.set_title('Разложение потока f = α₁·P₁ + α₂·P₂ + β·C',
                 fontsize=12, pad=8)
    save('fig_01_decomposition.png')


# =============================================================
# Figure 2 — Скэйлинг y/x — визуализация задачи 1
# =============================================================
def fig_scaling():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax in (ax1, ax2):
        ax.set_aspect('equal')
        ax.set_axis_off()

    def draw(ax, scale, title):
        P = {'s': (0, 1), 'a': (1.8, 2), 'b': (1.8, 0), 't': (3.6, 1)}
        edges = [('s', 'a', 4), ('s', 'b', 3), ('a', 't', 4), ('b', 't', 3)]
        for u, v, f in edges:
            val = f * scale
            lw = 1.0 + 0.8 * val
            draw_arrow(ax, P[u], P[v], lw=lw, color='#2E86DE')
            edge_label(ax, P[u], P[v], f'f={val:.1f}', fontsize=9)
        for name, p in P.items():
            if name in ('s', 't'):
                draw_node(ax, p, name, face='#fff3cd', edge='#b37400', r=0.22)
            else:
                draw_node(ax, p, name, r=0.22)
        ax.set_xlim(-0.5, 4.1)
        ax.set_ylim(-0.8, 2.8)
        ax.set_title(title, fontsize=11, pad=6)

    draw(ax1, 1.0,  'Исходный поток,  |f| = x = 7')
    draw(ax2, 4/7,  'Масштабированный f ′ = (y/x)·f,  |f ′| = y = 4')
    save('fig_02_scaling.png')


# =============================================================
# Figure 3 — Алгоритм поиска: вперёд до t или до цикла
# =============================================================
def fig_traversal():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    for ax in (ax1, ax2):
        ax.set_aspect('equal'); ax.set_axis_off()

    # Случай A: доходим до t  → путь
    Pa = {'s': (0, 1), 'u': (1.3, 1), 'v': (2.6, 1.7),
          'w': (3.9, 1.7), 't': (5.2, 1)}
    for e in [('s', 'u'), ('u', 'v'), ('v', 'w'), ('w', 't')]:
        draw_arrow(ax1, Pa[e[0]], Pa[e[1]], color='#2E86DE', lw=2.2)
    for name, p in Pa.items():
        face = '#fff3cd' if name in ('s', 't') else 'white'
        edge = '#b37400' if name in ('s', 't') else 'black'
        draw_node(ax1, p, name, face=face, edge=edge, r=0.22)
    ax1.text(0.5 * (Pa['u'][0] + Pa['v'][0]) + 0.1, 2.25,
             'старт: (u,v) с f>0', fontsize=9, color='#555')
    ax1.set_title('Случай А: дошли до t — выделяем путь s → … → t',
                  fontsize=11, pad=6)
    ax1.set_xlim(-0.5, 5.7); ax1.set_ylim(-0.2, 2.8)

    # Случай B: возврат в посещённую вершину → цикл
    Pb = {'s': (0, 1), 'u': (1.4, 1), 'v': (2.7, 1.7),
          'w': (4.0, 1.7), 'x': (2.7, 0.3), 't': (5.3, 1)}
    for e in [('s', 'u'), ('u', 'v'), ('v', 'w'), ('w', 'x'), ('x', 'v')]:
        col = '#EE5253' if e in [('v', 'w'), ('w', 'x'), ('x', 'v')] else '#777'
        lw = 2.4 if col == '#EE5253' else 1.6
        draw_arrow(ax2, Pb[e[0]], Pb[e[1]], color=col, lw=lw)
    for name, p in Pb.items():
        face = '#fff3cd' if name in ('s', 't') else 'white'
        edge = '#b37400' if name in ('s', 't') else 'black'
        draw_node(ax2, p, name, face=face, edge=edge, r=0.22)
    ax2.text(3.3, 1.05, 'цикл', fontsize=10, color='#EE5253',
             fontweight='bold')
    ax2.set_title('Случай Б: повторили вершину — выделяем цикл',
                  fontsize=11, pad=6)
    ax2.set_xlim(-0.5, 5.8); ax2.set_ylim(-0.2, 2.8)
    save('fig_03_traversal.png')


# =============================================================
# Figure 4 — Таблица итераций Форда-Фалкерсона (задача 3)
# =============================================================
def fig_integer_ff():
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.axis('off')
    data = [
        ['0', 'стартовый поток f₀ ≡ 0 ∈ ℤ', '—', '0'],
        ['1', 'путь s → a → t, c_res = (4, 3)', 'δ = min(4, 3) = 3', '3'],
        ['2', 'путь s → b → t, c_res = (5, 2)', 'δ = min(5, 2) = 2', '5'],
        ['3', 'путь s → a → b → t, c_res = (1, 3, 2)', 'δ = 1',     '6'],
        ['4', 'увеличивающих путей нет', '—', '6 (max)'],
    ]
    cols = ['Итер.', 'Событие в остаточной сети', 'bottleneck δ', '|f|']
    tbl = ax.table(cellText=data, colLabels=cols, cellLoc='center',
                   loc='center', colWidths=[0.07, 0.55, 0.2, 0.12])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.5)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor('#888')
        if r == 0:
            cell.set_facecolor('#f0f3f5')
            cell.set_text_props(weight='bold')
    ax.set_title('Целочисленность сохраняется на каждой итерации (все δ целые)',
                 fontsize=11, pad=8)
    save('fig_04_integer_ff.png')


# =============================================================
# Figure 5 — Сеть Форда-Фалкерсона на φ (задача 4)
# =============================================================
def fig_golden():
    fig, ax = base_ax((10, 4.2))
    P = {
        's': (0, 1.5),
        'a': (2.5, 3.0),
        'b': (2.5, 0.0),
        't': (5.0, 1.5),
    }
    # Основные рёбра (ёмкость M)
    big = [('s', 'a'), ('s', 'b'), ('a', 't'), ('b', 't')]
    for u, v in big:
        draw_arrow(ax, P[u], P[v], color='#2E86DE', lw=2.0)
        edge_label(ax, P[u], P[v], 'M', fontsize=11)

    # Тонкие рёбра
    draw_arrow(ax, P['a'], P['b'], color='#EE5253', lw=2.0)
    edge_label(ax, P['a'], P['b'], 'φ ≈ 0.618', fontsize=10, italic=True)
    draw_arrow(ax, P['b'], P['a'], color='#EE5253', lw=2.0)
    edge_label(ax, P['b'], P['a'], '1', fontsize=10, offset=-0.22)

    for name, p in P.items():
        if name in ('s', 't'):
            draw_node(ax, p, name, face='#fff3cd', edge='#b37400')
        else:
            draw_node(ax, p, name)

    ax.set_xlim(-0.5, 5.6)
    ax.set_ylim(-0.8, 3.6)
    ax.set_title('Контрпример: ёмкости M, 1 и φ = (√5−1)/2 — неудачный выбор '
                 'пути даёт бесконечный алгоритм', fontsize=11, pad=8)
    save('fig_05_golden.png')


# =============================================================
# Figure 6 — Неориентированное ребро → два направленных (задача 5)
# =============================================================
def fig_undirected_to_directed():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.2))
    for ax in (ax1, ax2):
        ax.set_aspect('equal'); ax.set_axis_off()

    # ДО: одно неориентированное
    u1, v1 = (0, 0.5), (3, 0.5)
    line = FancyArrowPatch(u1, v1, arrowstyle='-', lw=2.2, color='#555',
                           shrinkA=14, shrinkB=14)
    ax1.add_patch(line)
    draw_node(ax1, u1, 'u')
    draw_node(ax1, v1, 'v')
    ax1.text(1.5, 0.9, 'c(u,v)', ha='center', fontsize=11)
    ax1.set_title('Неориентированное ребро', fontsize=11, pad=6)
    ax1.set_xlim(-0.5, 3.5); ax1.set_ylim(-0.5, 1.6)

    # ПОСЛЕ: два направленных
    u2, v2 = (0, 0.5), (3, 0.5)
    draw_arrow(ax2, u2, v2, color='#2E86DE', lw=2.2)
    draw_arrow(ax2, v2, u2, color='#2E86DE', lw=2.2)
    draw_node(ax2, u2, 'u')
    draw_node(ax2, v2, 'v')
    ax2.text(1.5, 1.0, 'c(u,v)', ha='center', fontsize=11, color='#2E86DE')
    ax2.text(1.5, -0.05, 'c(u,v)', ha='center', fontsize=11, color='#2E86DE')
    ax2.set_title('Два направленных ребра той же ёмкости', fontsize=11, pad=6)
    ax2.set_xlim(-0.5, 3.5); ax2.set_ylim(-0.5, 1.6)
    save('fig_06_undirected.png')


# =============================================================
# Figure 7 — Рёберно непересекающиеся пути (задача 6)
# =============================================================
def fig_edge_disjoint():
    fig, ax = base_ax((10, 4.2))
    P = {
        's':  (0,  1.5),
        'a1': (1.8, 2.8),
        'a2': (1.8, 1.5),
        'a3': (1.8, 0.2),
        'b1': (3.6, 2.8),
        'b2': (3.6, 1.5),
        'b3': (3.6, 0.2),
        't':  (5.4, 1.5),
    }
    paths = [
        [('s', 'a1'), ('a1', 'b1'), ('b1', 't')],
        [('s', 'a2'), ('a2', 'b2'), ('b2', 't')],
        [('s', 'a3'), ('a3', 'b3'), ('b3', 't')],
    ]
    colors = ['#2E86DE', '#10AC84', '#EE5253']
    for path, color in zip(paths, colors):
        for u, v in path:
            draw_arrow(ax, P[u], P[v], color=color, lw=2.2)

    for name, p in P.items():
        face = '#fff3cd' if name in ('s', 't') else 'white'
        edge = '#b37400' if name in ('s', 't') else 'black'
        draw_node(ax, p, name, face=face, edge=edge, r=0.24)

    ax.set_xlim(-0.5, 6.0)
    ax.set_ylim(-0.6, 3.5)
    ax.set_title('Три рёберно непересекающихся пути s → t '
                 '(каждое ребро имеет ёмкость 1 ⟹ max flow = 3)',
                 fontsize=11, pad=8)
    save('fig_07_edge_disjoint.png')


# =============================================================
# Figure 8 — Vertex splitting (задача 7)
# =============================================================
def fig_vertex_split():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.4))
    for ax in (ax1, ax2):
        ax.set_aspect('equal'); ax.set_axis_off()

    # ДО: обычная вершина v
    P1 = {'a': (0, 1.8), 'b': (0, 0.2), 'v': (2.0, 1.0),
          'c': (4.0, 1.8), 'd': (4.0, 0.2)}
    for u, w in [('a', 'v'), ('b', 'v'), ('v', 'c'), ('v', 'd')]:
        draw_arrow(ax1, P1[u], P1[w], color='#555', lw=1.8)
    for name, p in P1.items():
        draw_node(ax1, p, name, r=0.22)
    ax1.set_title('До разбиения: вершина v', fontsize=11, pad=4)
    ax1.set_xlim(-0.6, 4.6); ax1.set_ylim(-0.4, 2.4)

    # ПОСЛЕ: разбитая v → v_in → v_out с ребром 1
    P2 = {'a': (0, 1.8), 'b': (0, 0.2), 'vi': (1.8, 1.0),
          'vo': (3.2, 1.0), 'c': (5.0, 1.8), 'd': (5.0, 0.2)}
    for u, w in [('a', 'vi'), ('b', 'vi')]:
        draw_arrow(ax2, P2[u], P2[w], color='#555', lw=1.8)
        edge_label(ax2, P2[u], P2[w], '∞', fontsize=9)
    for u, w in [('vo', 'c'), ('vo', 'd')]:
        draw_arrow(ax2, P2[u], P2[w], color='#555', lw=1.8)
        edge_label(ax2, P2[u], P2[w], '∞', fontsize=9)
    # внутреннее ребро ёмкости 1
    draw_arrow(ax2, P2['vi'], P2['vo'], color='#EE5253', lw=2.5)
    edge_label(ax2, P2['vi'], P2['vo'], '1', fontsize=11, color='#EE5253')

    draw_node(ax2, P2['a'], 'a', r=0.22)
    draw_node(ax2, P2['b'], 'b', r=0.22)
    draw_node(ax2, P2['vi'], 'vᵢₙ', r=0.26)   # v_in
    draw_node(ax2, P2['vo'], 'vₒᵤₜ', r=0.26)  # v_out
    draw_node(ax2, P2['c'], 'c', r=0.22)
    draw_node(ax2, P2['d'], 'd', r=0.22)
    ax2.set_title('После разбиения: v → (vᵢₙ, vₒᵤₜ) с внутренним ребром ёмкости 1',
                  fontsize=11, pad=4)
    ax2.set_xlim(-0.6, 5.6); ax2.set_ylim(-0.4, 2.4)
    save('fig_08_vertex_split.png')


# =============================================================
# Figure 9 — Задача о замках: поле и граф (задача 8)
# =============================================================
def fig_castles():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax in (ax1, ax2):
        ax.set_aspect('equal'); ax.set_axis_off()

    # Поле 5x4
    n, m = 4, 5
    grid = [
        # 0=free, 1=mountain, 2=castle, 3=wall(to build)
        [2, 0, 0, 0, 3],   # row 0: замок, свободные, застроенная
        [0, 1, 0, 0, 3],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 2],   # row 3: замок справа
    ]
    for r in range(n):
        for c in range(m):
            y = (n - 1 - r)
            x = c
            v = grid[r][c]
            colors = {0: '#ffffff', 1: '#8c7853', 2: '#ffd166', 3: '#ef476f'}
            rect = Rectangle((x, y), 1, 1, facecolor=colors[v],
                             edgecolor='#333', lw=1.2)
            ax1.add_patch(rect)
            label = {1: '▲', 2: '★', 3: '■'}.get(v, '')
            if label:
                ax1.text(x + 0.5, y + 0.5, label, ha='center', va='center',
                         fontsize=18, color='white' if v == 1 else 'black')

    legend = [
        mpatches.Patch(facecolor='#ffd166', edgecolor='#333', label='замки (s, t)'),
        mpatches.Patch(facecolor='#8c7853', edgecolor='#333', label='горы'),
        mpatches.Patch(facecolor='#ef476f', edgecolor='#333', label='застроенные клетки (min cut)'),
        mpatches.Patch(facecolor='#ffffff', edgecolor='#333', label='свободные'),
    ]
    ax1.legend(handles=legend, loc='upper center',
               bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False, fontsize=9)
    ax1.set_xlim(-0.3, m + 0.3)
    ax1.set_ylim(-1.4, n + 0.3)
    ax1.set_title('Поле n×m: замки, горы, минимальный «забор»', fontsize=11, pad=4)

    # Граф-модель: vertex split для свободной клетки
    P = {'s': (0, 1.5), 'vi': (1.5, 1.5), 'vo': (3.0, 1.5),
         'ui': (3.0, 0.3), 'uo': (4.5, 0.3),
         'wi': (3.0, 2.7), 'wo': (4.5, 2.7),
         't': (6.0, 1.5)}
    edges_inf = [('s', 'vi'), ('vo', 'ui'), ('vo', 'wi'),
                 ('uo', 't'), ('wo', 't')]
    for u, w in edges_inf:
        draw_arrow(ax2, P[u], P[w], color='#555', lw=1.5)
    # внутренние рёбра ёмкости 1
    for u, w in [('vi', 'vo'), ('ui', 'uo'), ('wi', 'wo')]:
        draw_arrow(ax2, P[u], P[w], color='#EE5253', lw=2.4)
        edge_label(ax2, P[u], P[w], '1', color='#EE5253', fontsize=10)

    for name, p in P.items():
        face = '#fff3cd' if name in ('s', 't') else 'white'
        edge = '#b37400' if name in ('s', 't') else 'black'
        r = 0.28 if name in ('s', 't') else 0.22
        draw_node(ax2, p, name, face=face, edge=edge, r=r)
    ax2.set_xlim(-0.5, 6.6); ax2.set_ylim(-0.6, 3.6)
    ax2.set_title('Сведение: vertex splitting, внутреннее ребро = 1',
                  fontsize=11, pad=4)
    save('fig_09_castles.png')


# =============================================================
# Figure 10 — Фабрики и магазины (задача 9)
# =============================================================
def fig_factories():
    fig, ax = base_ax((11, 4.8))
    P = {
        'S*': (-1.5, 1.5),
        'F1': (0.5, 2.6),
        'F2': (0.5, 0.4),
        'mid1': (2.8, 2.6),
        'mid2': (2.8, 0.4),
        'S1': (5.0, 2.6),
        'S2': (5.0, 0.4),
        'T*': (7.0, 1.5),
    }
    # Рёбра от суперисточника
    for f in ['F1', 'F2']:
        draw_arrow(ax, P['S*'], P[f], color='#555', lw=1.6)
        edge_label(ax, P['S*'], P[f], '1', fontsize=9)
    # Промежуточные рёбра графа
    for u, v in [('F1', 'mid1'), ('mid1', 'S1'),
                 ('F2', 'mid2'), ('mid2', 'S2')]:
        draw_arrow(ax, P[u], P[v], color='#2E86DE', lw=2.0)
    # К суперстоку
    for s in ['S1', 'S2']:
        draw_arrow(ax, P[s], P['T*'], color='#555', lw=1.6)
        edge_label(ax, P[s], P['T*'], '1', fontsize=9)

    specs = {
        'S*': ('#fff3cd', '#b37400'),
        'T*': ('#fff3cd', '#b37400'),
        'F1': ('#c8e6c9', '#2e7d32'),
        'F2': ('#c8e6c9', '#2e7d32'),
        'S1': ('#ffcdd2', '#c62828'),
        'S2': ('#ffcdd2', '#c62828'),
    }
    for name, p in P.items():
        face, edge = specs.get(name, ('white', 'black'))
        r = 0.32 if '*' in name else 0.26
        draw_node(ax, p, name, face=face, edge=edge, r=r)

    ax.text(0.5, 3.3, 'фабрики', fontsize=10, color='#2e7d32')
    ax.text(5.0, 3.3, 'магазины', fontsize=10, color='#c62828')
    ax.set_xlim(-2.2, 7.8); ax.set_ylim(-0.5, 3.8)
    ax.set_title('Суперисточник S* → фабрики → … → магазины → суперсток T* '
                 '(max flow = k ⟺ решение существует)', fontsize=11, pad=8)
    save('fig_10_factories.png')


# --------------------------
if __name__ == '__main__':
    print('Generating figures...')
    fig_decomposition()
    fig_scaling()
    fig_traversal()
    fig_integer_ff()
    fig_golden()
    fig_undirected_to_directed()
    fig_edge_disjoint()
    fig_vertex_split()
    fig_castles()
    fig_factories()
    print('Done.')
