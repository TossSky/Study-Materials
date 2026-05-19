"""
Рисунки к ДЗ: блоки 5, 6, 9 — 10 задач.
Все картинки сохраняются в figs_dz/*.png рядом со скриптом.
"""
import os, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle, FancyBboxPatch
import networkx as nx

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.linewidth': 0,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.10,
    'savefig.facecolor': 'white',
})

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figs_dz')
os.makedirs(OUT, exist_ok=True)


def save(name):
    path = os.path.join(OUT, name)
    plt.savefig(path)
    plt.close()
    print('  ->', name)


def base_ax(figsize=(9, 5)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect('equal')
    ax.set_axis_off()
    return fig, ax


def draw_arrow(ax, p1, p2, *, color='black', lw=1.6, shrink=14, style='-|>', zorder=2,
               connectionstyle='arc3,rad=0'):
    arrow = FancyArrowPatch(
        p1, p2, arrowstyle=style, color=color, lw=lw, mutation_scale=14,
        shrinkA=shrink, shrinkB=shrink, zorder=zorder, connectionstyle=connectionstyle,
    )
    ax.add_patch(arrow)


def draw_edge(ax, p1, p2, *, color='black', lw=1.6, shrink=14, zorder=2):
    arrow = FancyArrowPatch(
        p1, p2, arrowstyle='-', color=color, lw=lw, shrinkA=shrink, shrinkB=shrink,
        zorder=zorder,
    )
    ax.add_patch(arrow)


def draw_node(ax, pos, label, *, r=0.30, face='white', edge='black',
              text_color='black', lw=1.8, fontsize=12):
    c = Circle(pos, r, facecolor=face, edgecolor=edge, lw=lw, zorder=3)
    ax.add_patch(c)
    ax.text(pos[0], pos[1], label, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color=text_color, zorder=4)


def edge_label(ax, p1, p2, text, *, offset=0.22, color='black', fontsize=10, italic=False):
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy) or 1.0
    nx_, ny_ = -dy / L, dx / L
    tx, ty = mx + offset * nx_, my + offset * ny_
    ax.text(tx, ty, text, ha='center', va='center', color=color,
            fontsize=fontsize, fontstyle='italic' if italic else 'normal', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=1.4))


# ======================================================
# Блок 5, задача 1 — Обобщение Кэли (лес из k компонент)
# ======================================================
def fig_b5_t1_forest():
    fig, ax = base_ax((11, 4.6))
    # Три компоненты: c1=3, c2=2, c3=4. n=9. k=3.
    C1 = {'a1': (0.5, 3.3), 'a2': (1.6, 3.8), 'a3': (1.5, 2.6)}
    C2 = {'b1': (4.0, 3.5), 'b2': (5.0, 3.0)}
    C3 = {'c1': (7.5, 3.6), 'c2': (8.7, 3.2), 'c3': (8.5, 2.0), 'c4': (7.4, 2.4)}
    edges_inside = [('a1', 'a2'), ('a2', 'a3'),
                    ('b1', 'b2'),
                    ('c1', 'c2'), ('c2', 'c3'), ('c3', 'c4')]
    pos = {**C1, **C2, **C3}
    for u, v in edges_inside:
        draw_edge(ax, pos[u], pos[v], color='#666', lw=1.8)
    for name, p in pos.items():
        if name.startswith('a'):
            draw_node(ax, p, name, face='#cfe2ff', edge='#1d4e89', r=0.25, fontsize=10)
        elif name.startswith('b'):
            draw_node(ax, p, name, face='#d4edda', edge='#1f7a3a', r=0.25, fontsize=10)
        else:
            draw_node(ax, p, name, face='#fff3cd', edge='#b37400', r=0.25, fontsize=10)
    # Добавленные межкомпонентные рёбра — пунктиром, красные
    cross = [('a2', 'b1'), ('b2', 'c4')]
    for u, v in cross:
        arrow = FancyArrowPatch(pos[u], pos[v], arrowstyle='-', color='#EE5253',
                                lw=2.4, shrinkA=12, shrinkB=12, linestyle='--')
        ax.add_patch(arrow)
    # подписи к компонентам
    ax.text(1.0, 4.5, '$C_1$, $|C_1|=c_1=3$', fontsize=11, color='#1d4e89')
    ax.text(4.3, 4.3, '$C_2$, $c_2=2$', fontsize=11, color='#1f7a3a')
    ax.text(7.7, 4.6, '$C_3$, $c_3=4$', fontsize=11, color='#b37400')
    ax.text(2.5, 0.6, '$k-1=2$ красных пунктирных ребра соединяют компоненты в дерево',
            fontsize=11, color='#EE5253')
    ax.set_xlim(-0.5, 10.0)
    ax.set_ylim(0.2, 5.0)
    ax.set_title('Лес из $k$ компонент: добавляем $k-1$ ребро, чтобы получить дерево',
                 fontsize=12, pad=8)
    save('b5_t1_forest.png')


# ======================================================
# Блок 5, задача 3 — K5 (граф для эйлеровых циклов)
# ======================================================
def fig_b5_t3_k5():
    fig, ax = base_ax((6.5, 6.5))
    n = 5
    R = 2.4
    pos = {}
    for i in range(n):
        ang = math.pi/2 + 2*math.pi*i/n
        pos[i+1] = (R*math.cos(ang), R*math.sin(ang))
    # Все рёбра K5
    for u in range(1, n+1):
        for v in range(u+1, n+1):
            draw_edge(ax, pos[u], pos[v], color='#3870b3', lw=1.8)
    for v, p in pos.items():
        draw_node(ax, p, str(v), face='#fff3cd', edge='#b37400', r=0.30, fontsize=14)
    ax.set_xlim(-3.2, 3.2); ax.set_ylim(-3.0, 3.5)
    ax.set_title('$K_5$: все вершины степени 4 (чётно) ⟹ существует эйлеров цикл',
                 fontsize=11, pad=8)
    save('b5_t3_k5.png')


# ======================================================
# Блок 5, задача 11 — Антихватал, контрпример
# ======================================================
def fig_b5_t11_antichvatal():
    fig, ax = base_ax((10, 5.4))
    # n=7, i=2. A=2 независимые верш., B=3 (нет рёбер ни в A, ни в B, ни A↔B), C=2 клика
    # |A|=2, |B|=3, |C|=2. Степени: A,B → 2 (соединены только с C). C → (1)+(2)+(3) = n-1 = 6
    A = {'a1': (-3.0, 1.0), 'a2': (-3.0, -1.0)}
    B = {'b1': (-1.0, 2.4), 'b2': (-1.0, 0.0), 'b3': (-1.0, -2.4)}
    C = {'c1': (1.5, 1.0), 'c2': (1.5, -1.0)}
    pos = {**A, **B, **C}
    # Рёбра между {A∪B} и C
    for u in list(A) + list(B):
        for v in C:
            draw_edge(ax, pos[u], pos[v], color='#888', lw=1.2)
    # Клика C
    draw_edge(ax, pos['c1'], pos['c2'], color='#EE5253', lw=2.6)
    for name, p in A.items():
        draw_node(ax, p, name, face='#cfe2ff', edge='#1d4e89', r=0.28, fontsize=10)
    for name, p in B.items():
        draw_node(ax, p, name, face='#d4edda', edge='#1f7a3a', r=0.28, fontsize=10)
    for name, p in C.items():
        draw_node(ax, p, name, face='#ffd6d6', edge='#b03030', r=0.30, fontsize=11)
    ax.text(-3.5, 2.3, '$A$ — независ. множество\n$|A|=i=2$, $\\deg=2$',
            fontsize=10, color='#1d4e89')
    ax.text(-1.5, 3.4, '$B$ — независ.,\n$|B|=n-2i=3$, $\\deg=2$', fontsize=10,
            color='#1f7a3a')
    ax.text(1.5, 2.3, '$C$ — клика\n$|C|=i=2$, $\\deg=n-1=6$', fontsize=10, color='#b03030')
    ax.text(-3.4, -3.2, 'Удаляем $C$ ⟹ $|A|+|B|=n-i=5$ изолированных вершин ⟹\n$5 > i=2$ компонент ⟹ граф НЕ гамильтонов.',
            fontsize=10, color='#222')
    ax.set_xlim(-4.0, 3.5); ax.set_ylim(-4.0, 3.7)
    ax.set_title('Контрпример к гамильтоновости: $i=2$, $n=7$. '
                 'Степ. посл. $(2,2,2,2,2,6,6)$ нарушает условие Хватала',
                 fontsize=11, pad=6)
    save('b5_t11_antichvatal.png')


# ======================================================
# Блок 6, задача 7 — 2-SAT, импликационный граф
# ======================================================
def fig_b6_t7_implication():
    fig, ax = base_ax((10, 4.6))
    pos = {
        'x1': (0, 2.5), '!x1': (0, 0.5),
        'x2': (3, 2.5), '!x2': (3, 0.5),
        'x3': (6, 2.5), '!x3': (6, 0.5),
        'x4': (9, 2.5), '!x4': (9, 0.5),
    }
    # Импликации (пример) для (x1∨x2) ∧ (¬x2∨x3) ∧ (¬x3∨¬x4) ∧ (x4∨x1):
    impls = [('!x1','x2'), ('!x2','x1'),
             ('x2','x3'), ('!x3','!x2'),
             ('x3','!x4'), ('x4','!x3'),
             ('!x4','x1'), ('!x1','x4')]
    for u, v in impls:
        draw_arrow(ax, pos[u], pos[v], color='#3870b3', lw=1.4, shrink=14,
                   connectionstyle='arc3,rad=0.18')
    for name, p in pos.items():
        face = '#cfe2ff' if not name.startswith('!') else '#ffd6d6'
        edge = '#1d4e89' if not name.startswith('!') else '#b03030'
        lab = name.replace('!', '¬')
        draw_node(ax, p, lab, face=face, edge=edge, r=0.30, fontsize=11)
    ax.text(-1.0, 3.5, 'Литералы $x_i$ — синие, $\\neg x_i$ — красные. '
            'Каждый дизъюнкт $(\\ell_1 \\vee \\ell_2)$ ⟹ две дуги: $\\neg\\ell_1 \\Rightarrow \\ell_2$ и $\\neg\\ell_2 \\Rightarrow \\ell_1$.',
            fontsize=10)
    ax.set_xlim(-1.2, 10.5); ax.set_ylim(-0.5, 4.2)
    ax.set_title('Импликационный граф $G_{\\text{2-SAT}}$', fontsize=12, pad=6)
    save('b6_t7_implication.png')


# ======================================================
# Блок 6, задача 8 — list coloring → 2-SAT
# ======================================================
def fig_b6_t8_listcolor():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax in (ax1, ax2):
        ax.set_aspect('equal'); ax.set_axis_off()
    # Слева: маленький граф из 4 вершин с запретами цветов
    pos = {'u': (0.0, 1.5), 'v': (2.2, 2.6), 'w': (2.2, 0.4), 'z': (4.4, 1.5)}
    for u, v in [('u','v'),('u','w'),('v','w'),('v','z'),('w','z')]:
        draw_edge(ax1, pos[u], pos[v], color='#666', lw=1.6)
    forbid = {'u': 1, 'v': 2, 'w': 3, 'z': 1}  # запрещ. цвет (1,2,3 = R,G,B)
    palette = {1: '#EE5253', 2: '#10AC84', 3: '#3870b3'}
    for name, p in pos.items():
        c = forbid[name]
        draw_node(ax1, p, name, r=0.34, face='white', edge='black')
        ax1.text(p[0], p[1]-0.55, f'нельзя {c}', ha='center', fontsize=9,
                 color=palette[c])
        # Доступные цвета — два кружочка-тика
        ok = [x for x in (1,2,3) if x != c]
        for k, col in enumerate(ok):
            tick = Circle((p[0]-0.18 + 0.18*k, p[1]+0.65), 0.10,
                          facecolor=palette[col], edgecolor='black', lw=0.6)
            ax1.add_patch(tick)
    ax1.set_xlim(-1, 5.5); ax1.set_ylim(-0.6, 3.6)
    ax1.set_title('Граф со списками $|L(v)|=2$ для каждой вершины', fontsize=11, pad=6)

    # Справа: соответствующая 2-SAT клоза
    ax2.text(0.05, 0.92, '2-SAT-кодирование:', fontsize=12, fontweight='bold',
             transform=ax2.transAxes)
    txt = (
        '• Перем. $x_v \\in \\{0,1\\}$:\n'
        '   $x_v=0$ ⟺ цвет = $a_v$, $x_v=1$ ⟺ цвет = $b_v$\n'
        '• Ребро $(u,v)$, цвета совпадают при $(x_u, x_v) = (\\alpha, \\beta)$ ⟹\n'
        '   запрет: дизъюнкт $(\\bar\\ell_u \\vee \\bar\\ell_v)$\n'
        '• Списки длины 2 ⟹ ≤ 2 запретов на ребро ⟹ 2-CNF\n\n'
        'Решение 2-SAT за $O(n+m)$ через SCC.'
    )
    ax2.text(0.05, 0.08, txt, fontsize=11, transform=ax2.transAxes, va='bottom')
    ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
    save('b6_t8_listcolor.png')


# ======================================================
# Блок 6, задача 9 — вечеринка Пети
# ======================================================
def fig_b6_t9_party():
    fig, ax = base_ax((10, 4.6))
    pos = {
        'P': (0, 2.5), '!P': (0, 0.5),
        'G': (2.6, 2.5), '!G': (2.6, 0.5),
        'M': (5.2, 2.5), '!M': (5.2, 0.5),
        'I': (7.8, 2.5), '!I': (7.8, 0.5),
    }
    # «P приду только если придет G» = P → G  ⟹  ¬G → ¬P
    # «Если будет M — меня (I) не будет»     = M → ¬I  ⟹  I → ¬M
    impls = [('P','G'), ('!G','!P'),
             ('M','!I'), ('I','!M')]
    for u, v in impls:
        draw_arrow(ax, pos[u], pos[v], color='#3870b3', lw=1.6,
                   connectionstyle='arc3,rad=0.20')
    for name, p in pos.items():
        face = '#cfe2ff' if not name.startswith('!') else '#ffd6d6'
        edge = '#1d4e89' if not name.startswith('!') else '#b03030'
        lab = name.replace('!', '¬')
        draw_node(ax, p, lab, face=face, edge=edge, r=0.34, fontsize=12)
    # подписи — литералы это «человек придёт / не придёт»
    for x, name in [(0,'Петя'), (2.6,'Гена'), (5.2,'Марина'), (7.8,'Иван')]:
        ax.text(x, 3.2, name, ha='center', fontsize=10, color='#222')
    ax.text(-0.8, -0.3, 'Каждое требование — импликация $(\\ell \\Rightarrow \\ell\') $ '
            '$\\equiv$ дизъюнкт $(\\bar\\ell \\vee \\ell\\,\')$ ⟹ задача — 2-SAT.',
            fontsize=10)
    ax.set_xlim(-1.2, 9.0); ax.set_ylim(-0.8, 3.7)
    ax.set_title('Вечеринка Пети: модель в виде импликационного графа',
                 fontsize=11, pad=6)
    save('b6_t9_party.png')


# ======================================================
# Блок 6, задача 10 — топливный бак, minimax
# ======================================================
def fig_b6_t10_fuel():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax in (ax1, ax2):
        ax.set_aspect('equal'); ax.set_axis_off()
    pos = {1:(0,2), 2:(2,3), 3:(2,1), 4:(4,2), 5:(6,3), 6:(6,1)}
    edges = [(1,2,5),(1,3,8),(2,3,3),(2,4,7),(3,4,4),(4,5,6),(4,6,9),(5,6,2)]
    # Слева — исходный полный (точнее, реальный) граф
    for u, v, w in edges:
        draw_edge(ax1, pos[u], pos[v], color='#666', lw=1.4)
        edge_label(ax1, pos[u], pos[v], str(w), fontsize=10)
    for v, p in pos.items():
        draw_node(ax1, p, str(v), r=0.27, face='#fff3cd', edge='#b37400', fontsize=11)
    ax1.set_xlim(-0.6, 7); ax1.set_ylim(-0.4, 4.1)
    ax1.set_title('Исходный граф: вес ребра = расход топлива', fontsize=11, pad=6)

    # Справа — рёбра с весом ≤ B = 7 (например), показывает связность
    B = 7
    for u, v, w in edges:
        col = '#10AC84' if w <= B else '#dddddd'
        lw = 2.4 if w <= B else 1.0
        draw_edge(ax2, pos[u], pos[v], color=col, lw=lw)
        edge_label(ax2, pos[u], pos[v], str(w),
                   color=col if w<=B else '#aaa', fontsize=10)
    for v, p in pos.items():
        draw_node(ax2, p, str(v), r=0.27, face='#fff3cd', edge='#b37400', fontsize=11)
    ax2.set_xlim(-0.6, 7); ax2.set_ylim(-0.4, 4.1)
    ax2.set_title(f'Бак $B={B}$: оставлены рёбра с $w \\leq B$. Граф связен — годится',
                  fontsize=11, pad=6)
    save('b6_t10_fuel.png')


# ======================================================
# Блок 9, задача 1 — сетевой план (DAG из 8 работ)
# ======================================================
def fig_b9_t1_network():
    fig, ax = base_ax((12, 6.0))
    # Расположим по «уровням» топсорта
    pos = {
        8: (0.5, 3.0),
        5: (3.0, 4.6),
        7: (3.0, 1.4),
        3: (3.0, 3.0),
        6: (5.5, 2.2),
        4: (8.0, 3.6),
        2: (10.5, 1.6),
        1: (10.5, 4.4),
    }
    # Рёбра: предш(i) → i, на ребре — длительность работы-источника
    edges = [(8,3,2),(8,5,2),(8,7,2),
             (3,1,6),(3,2,6),(3,4,6),(3,6,6),
             (5,4,2),(5,6,2),
             (6,2,3),(6,4,3),
             (7,6,4),
             (4,1,3)]
    for u, v, _ in edges:
        draw_arrow(ax, pos[u], pos[v], color='#3870b3', lw=1.6, shrink=18)
    tm = {1:5,2:4,3:6,4:3,5:2,6:3,7:4,8:2}
    crit = {1, 4, 6, 3, 8}
    for v, p in pos.items():
        if v in crit:
            draw_node(ax, p, f'{v}\nt={tm[v]}', face='#ffd6d6', edge='#b03030',
                      r=0.42, fontsize=10)
        else:
            draw_node(ax, p, f'{v}\nt={tm[v]}', face='#fff3cd', edge='#b37400',
                      r=0.42, fontsize=10)
    # Подсветим критический путь
    crit_edges = [(8,3),(3,6),(6,4),(4,1)]
    for u, v in crit_edges:
        draw_arrow(ax, pos[u], pos[v], color='#EE5253', lw=3.2, shrink=20)
    ax.text(0.5, 5.7, 'Критический путь $8 \\to 3 \\to 6 \\to 4 \\to 1$, $T_{кр}=2+6+3+3+5=19$',
            fontsize=11, color='#EE5253', fontweight='bold')
    ax.set_xlim(-0.6, 11.6); ax.set_ylim(0.0, 6.2)
    ax.set_title('DAG задачи сетевого планирования (внутри узла — номер работы и длительность)',
                 fontsize=11, pad=6)
    save('b9_t1_network.png')


# ======================================================
# Блок 9, задача 2 — диаграмма Ганта c резервами
# ======================================================
def fig_b9_t2_gantt():
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_axis_off()
    # ebeg, efin, lbeg, lfin
    data = {
        8: (0, 2, 11, 13),
        5: (2, 4, 17, 19),
        7: (2, 6, 15, 19),
        3: (2, 8, 13, 19),
        6: (8, 11, 19, 22),
        4: (11, 14, 22, 25),
        2: (11, 15, 26, 30),
        1: (14, 19, 25, 30),
    }
    order = [8, 5, 7, 3, 6, 4, 2, 1]
    y0 = 0.5
    h = 0.6
    Tz = 30
    for i, w in enumerate(order):
        ebeg, efin, lbeg, lfin = data[w]
        y = (len(order) - 1 - i) + y0
        # ранний интервал — синий
        ax.add_patch(Rectangle((ebeg, y), efin-ebeg, h, facecolor='#3870b3',
                               edgecolor='black', lw=0.8, alpha=0.8))
        # резерв (от efin до lfin) — серая полоса
        ax.add_patch(Rectangle((efin, y+0.15), lfin-efin, h-0.30, facecolor='#dddddd',
                               edgecolor='#888', lw=0.6, hatch='///'))
        # поздний интервал (для контекста — пунктир)
        ax.add_patch(Rectangle((lbeg, y), lfin-lbeg, h, facecolor='none',
                               edgecolor='#b03030', lw=1.2, linestyle='--'))
        ax.text(-1, y+h/2, f'работа {w}', ha='right', va='center', fontsize=10)
        ax.text(ebeg-0.2, y+h+0.05, f'{ebeg}', ha='right', fontsize=8, color='#333')
        ax.text(efin+0.1, y+h+0.05, f'{efin}', ha='left', fontsize=8, color='#333')
        ax.text(lfin+0.1, y-0.05, f'{lfin}', ha='left', fontsize=8, color='#b03030')
    # ось времени
    ax.plot([0, Tz], [-0.4, -0.4], color='black', lw=1)
    for t in range(0, Tz+1, 2):
        ax.plot([t, t], [-0.5, -0.3], color='black', lw=1)
        ax.text(t, -0.85, str(t), ha='center', fontsize=8)
    ax.text(Tz, -1.3, f'$T_з={Tz}$', ha='right', fontsize=11, color='black')
    ax.set_xlim(-3.5, Tz+1)
    ax.set_ylim(-1.7, len(order)+0.2)
    legend = [
        mpatches.Patch(facecolor='#3870b3', edgecolor='black', label='ранний интервал [ebeg, efin]'),
        mpatches.Patch(facecolor='#dddddd', edgecolor='#888', hatch='///',
                       label='полный резерв $r=lfin-efin$'),
        mpatches.Patch(facecolor='none', edgecolor='#b03030', linestyle='--',
                       label='поздний интервал [lbeg, lfin]'),
    ]
    ax.legend(handles=legend, loc='upper center',
              bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False, fontsize=10)
    ax.set_title('Диаграмма Ганта при $T_з=30$: ранние и поздние интервалы, резерв',
                 fontsize=11, pad=8)
    save('b9_t2_gantt.png')


# ======================================================
# Блок 9, задача 3 — взвешенный граф для MaxMin (узкие места)
# ======================================================
def fig_b9_t3_graph(highlight_path=False):
    fig, ax = base_ax((10, 6.5))
    pos = {
        1: (0.0, 3.0),
        2: (2.5, 5.0),
        3: (2.5, 1.0),
        4: (5.0, 3.0),
        5: (7.5, 5.0),
        6: (7.5, 1.0),
        7: (10.0, 3.0),
    }
    edges = [
        (1,2,5),(1,3,3),
        (2,4,2),(2,5,3),
        (3,2,1),(3,4,6),(3,6,4),
        (4,1,1),(4,5,1),(4,6,1),(4,7,4),
        (5,6,12),(5,7,1),
        (6,4,3),(6,7,2),
    ]
    path_edges = {(1,3),(3,4),(4,7)} if highlight_path else set()
    for u, v, w in edges:
        is_p = (u, v) in path_edges
        col = '#EE5253' if is_p else '#3870b3'
        lw = 3.2 if is_p else 1.5
        rad = 0.15 if (v, u, ) in [(b,a) for (a,b,_) in edges] else 0.0
        draw_arrow(ax, pos[u], pos[v], color=col, lw=lw, shrink=18,
                   connectionstyle=f'arc3,rad={rad}')
        edge_label(ax, pos[u], pos[v], str(w),
                   color=col if is_p else 'black', fontsize=10,
                   offset=0.30 if rad != 0 else 0.22)
    for v, p in pos.items():
        if v == 1:
            draw_node(ax, p, '1', face='#d4edda', edge='#1f7a3a', r=0.34, fontsize=12)
        elif v == 7:
            draw_node(ax, p, '7', face='#ffd6d6', edge='#b03030', r=0.34, fontsize=12)
        else:
            draw_node(ax, p, str(v), face='#fff3cd', edge='#b37400', r=0.32, fontsize=12)
    ax.text(0, 5.7, 'Источник $s=1$, сток $t=7$.', fontsize=11)
    if highlight_path:
        ax.text(2.0, 0.0, 'MaxMin путь: $1 \\to 3 \\to 4 \\to 7$, веса $(3, 6, 4)$, '
                'узкое место $= \\min = 3$.',
                fontsize=11, color='#EE5253', fontweight='bold')
    ax.set_xlim(-0.6, 10.8); ax.set_ylim(-0.7, 6.2)
    title = 'Взвешенный орграф $G$' if not highlight_path else 'Итоговый MaxMin-путь'
    ax.set_title(title, fontsize=12, pad=6)
    save('b9_t3_graph.png' if not highlight_path else 'b9_t3_path.png')


if __name__ == '__main__':
    print('Generating figures for ДЗ ...')
    fig_b5_t1_forest()
    fig_b5_t3_k5()
    fig_b5_t11_antichvatal()
    fig_b6_t7_implication()
    fig_b6_t8_listcolor()
    fig_b6_t9_party()
    fig_b6_t10_fuel()
    fig_b9_t1_network()
    fig_b9_t2_gantt()
    fig_b9_t3_graph(highlight_path=False)
    fig_b9_t3_graph(highlight_path=True)
    print('Done.')
