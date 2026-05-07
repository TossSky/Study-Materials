# -*- coding: utf-8 -*-
"""Сборка Jupyter Notebook — исполняемое приложение к отчёту.
Код, численный вывод и графики; полный текст обзора и выводов — в DOCX."""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell(
    "# Курсовая работа по ТВиМС — Вариант 9 (Log-Laplace)\n"
    "\n"
    "**Студент:** Тоцкий В., гр. 5151003/40001  \n"
    "**Преподаватель:** Пахомова О. А."
))

# Считывание
cells.append(nbf.v4.new_markdown_cell(
    "## Считывание выборки"
))
cells.append(nbf.v4.new_code_cell(
    "import csv, math\n"
    "import numpy as np\n"
    "import matplotlib.pyplot as plt\n"
    "\n"
    "RNG = np.random.default_rng(20260507)\n"
    "\n"
    "with open('var_9_loglaplace.csv', encoding='utf-8') as f:\n"
    "    sample = [float(row[0]) for row in csv.reader(f) if row]\n"
    "n = len(sample)\n"
    "print(f'n = {n}, x_min = {min(sample):.6f}, x_max = {max(sample):.6f}')"
))

# Статистики
cells.append(nbf.v4.new_markdown_cell(
    "## Выборочные статистики\n"
    "\n"
    "Функции реализованы вручную, без обращения к `numpy.mean`, "
    "`statistics.median` и т. п."
))
cells.append(nbf.v4.new_code_cell(
    "def s_sum(x):           return sum(x)\n"
    "def s_mean(x):          return s_sum(x) / len(x)\n"
    "def s_range(x):         return max(x) - min(x)\n"
    "\n"
    "def s_median(x):\n"
    "    s = sorted(x); k = len(s)\n"
    "    return s[k // 2] if k % 2 else 0.5 * (s[k // 2 - 1] + s[k // 2])\n"
    "\n"
    "def s_mode(x, decimals=2):\n"
    "    cnt = {}\n"
    "    for v in x:\n"
    "        key = round(v, decimals)\n"
    "        cnt[key] = cnt.get(key, 0) + 1\n"
    "    m = max(cnt.values())\n"
    "    return sorted(k for k, c in cnt.items() if c == m), m\n"
    "\n"
    "def s_var_biased(x):\n"
    "    m = s_mean(x)\n"
    "    return sum((v - m) ** 2 for v in x) / len(x)\n"
    "\n"
    "def s_var_unbiased(x):\n"
    "    m = s_mean(x)\n"
    "    return sum((v - m) ** 2 for v in x) / (len(x) - 1)\n"
    "\n"
    "def s_initial_moment(x, k):  return sum(v ** k for v in x) / len(x)\n"
    "\n"
    "def s_central_moment(x, k):\n"
    "    m = s_mean(x)\n"
    "    return sum((v - m) ** k for v in x) / len(x)"
))
cells.append(nbf.v4.new_code_cell(
    "modes, mcnt = s_mode(sample)\n"
    "print(f'Сумма                       {s_sum(sample):.6f}')\n"
    "print(f'Выборочное среднее          {s_mean(sample):.6f}')\n"
    "print(f'Медиана                     {s_median(sample):.6f}')\n"
    "print(f'Мода (округл. 0.01)         {modes[0]:.2f}  (частота {mcnt})')\n"
    "print(f'Минимум, максимум           {min(sample):.6f}, {max(sample):.6f}')\n"
    "print(f'Размах                      {s_range(sample):.6f}')\n"
    "print(f'Смещ. дисперсия D           {s_var_biased(sample):.6f}')\n"
    "print(f'Несмещ. дисперсия s^2       {s_var_unbiased(sample):.6f}')\n"
    "print(f'Нач. момент 3-го порядка    {s_initial_moment(sample, 3):.6f}')\n"
    "print(f'Нач. момент 4-го порядка    {s_initial_moment(sample, 4):.6f}')\n"
    "print(f'Центр. момент 3-го порядка  {s_central_moment(sample, 3):.6f}')\n"
    "print(f'Центр. момент 4-го порядка  {s_central_moment(sample, 4):.6f}')"
))

# ЭФР
cells.append(nbf.v4.new_markdown_cell(
    "## Эмпирическая функция распределения\n"
    "\n"
    "$$F_n(x) = \\dfrac{1}{n}\\,|\\{i : x_i \\le x\\}|$$"
))
cells.append(nbf.v4.new_code_cell(
    "def ecdf(s):\n"
    "    s = sorted(s); k = len(s)\n"
    "    return s, [(i + 1) / k for i in range(k)]\n"
    "\n"
    "def plot_ecdf(s, title, ax):\n"
    "    xs, fs = ecdf(s)\n"
    "    pad = (max(xs) - min(xs)) * 0.05 or 0.05\n"
    "    ax.step([min(xs) - pad] + xs, [0.0] + fs, where='post', lw=1.5)\n"
    "    ax.scatter(xs, fs, s=12, zorder=3)\n"
    "    ax.set(xlabel='x', ylabel='$F_n(x)$', title=title)\n"
    "    ax.grid(True, ls='--', alpha=0.5)\n"
    "\n"
    "fig, ax = plt.subplots(2, 2, figsize=(12, 8))\n"
    "for a, k in zip(ax.flat[:3], (10, 100, 200)):\n"
    "    sub = [sample[i] for i in RNG.choice(n, k, replace=False)]\n"
    "    plot_ecdf(sub, f'ЭФР, n = {k}', a)\n"
    "plot_ecdf(sample, f'ЭФР, n = {n} (полная)', ax[1, 1])\n"
    "plt.tight_layout(); plt.show()"
))

# Гистограмма
cells.append(nbf.v4.new_markdown_cell(
    "## Гистограмма\n"
    "\n"
    "$$h_i = \\dfrac{n_i}{n\\,\\Delta_i}, \\quad k = \\mathrm{round}(1 + \\log_2 n)$$"
))
cells.append(nbf.v4.new_code_cell(
    "def histogram(s, bins=None):\n"
    "    k = len(s)\n"
    "    if bins is None:\n"
    "        bins = max(1, round(1 + math.log2(k)))\n"
    "    a, b = min(s), max(s)\n"
    "    if a == b: b = a + 1.0\n"
    "    edges = [a + (b - a) * i / bins for i in range(bins + 1)]\n"
    "    counts = [0] * bins\n"
    "    for v in s:\n"
    "        idx = min(int((v - a) / (b - a) * bins), bins - 1)\n"
    "        counts[idx] += 1\n"
    "    dx = (b - a) / bins\n"
    "    return edges, counts, [c / (k * dx) for c in counts]\n"
    "\n"
    "def plot_hist(s, title, ax):\n"
    "    edges, _, dens = histogram(s)\n"
    "    w = [edges[i+1] - edges[i] for i in range(len(edges) - 1)]\n"
    "    c = [(edges[i] + edges[i+1]) / 2 for i in range(len(edges) - 1)]\n"
    "    ax.bar(c, dens, width=w, edgecolor='black', color='#4C72B0', alpha=0.75)\n"
    "    ax.set(xlabel='x', ylabel='плотность', title=title)\n"
    "    ax.grid(True, ls='--', alpha=0.5)\n"
    "\n"
    "fig, ax = plt.subplots(2, 2, figsize=(12, 8))\n"
    "for a, k in zip(ax.flat[:3], (10, 100, 200)):\n"
    "    sub = [sample[i] for i in RNG.choice(n, k, replace=False)]\n"
    "    plot_hist(sub, f'n = {k}', a)\n"
    "plot_hist(sample, f'n = {n} (полная)', ax[1, 1])\n"
    "plt.tight_layout(); plt.show()"
))

# Теоретическая функция
cells.append(nbf.v4.new_markdown_cell(
    "## Теоретическая функция распределения Log-Laplace\n"
    "\n"
    "$$f(x;\\mu,b) = \\dfrac{1}{2bx}\\,e^{-|\\ln x - \\mu| / b}, \\quad x > 0$$"
))
cells.append(nbf.v4.new_code_cell(
    "def loglaplace_pdf(x, mu, b):\n"
    "    if x <= 0: return 0.0\n"
    "    return math.exp(-abs(math.log(x) - mu) / b) / (2 * b * x)\n"
    "\n"
    "def loglaplace_cdf(x, mu, b):\n"
    "    if x <= 0: return 0.0\n"
    "    z = math.log(x) - mu\n"
    "    return 0.5 * math.exp(z / b) if z <= 0 else 1.0 - 0.5 * math.exp(-z / b)"
))
cells.append(nbf.v4.new_code_cell(
    "x_grid = np.linspace(3.5, 13.0, 800)\n"
    "fig, ax = plt.subplots(1, 2, figsize=(13, 5))\n"
    "\n"
    "# Влияние mu (b фиксирован)\n"
    "for mu in (1.50, 2.20):\n"
    "    F = [loglaplace_cdf(x, mu, 0.05) for x in x_grid]\n"
    "    ax[0].plot(x_grid, F, lw=1.8, label=fr'$\\mu={mu:.2f}$, $b=0.05$')\n"
    "ax[0].set(xlabel='x', ylabel='F(x)', title='Влияние μ (b = 0.05)')\n"
    "ax[0].grid(True, ls='--', alpha=0.5); ax[0].legend()\n"
    "\n"
    "# Влияние b (mu фиксирован)\n"
    "for b in (0.01, 0.10):\n"
    "    F = [loglaplace_cdf(x, 1.97, b) for x in x_grid]\n"
    "    ax[1].plot(x_grid, F, lw=1.8, label=fr'$\\mu=1.97$, $b={b:.2f}$')\n"
    "ax[1].set(xlabel='x', ylabel='F(x)', title='Влияние b (μ = 1.97)')\n"
    "ax[1].grid(True, ls='--', alpha=0.5); ax[1].legend()\n"
    "\n"
    "plt.tight_layout(); plt.show()"
))

# Совмещение ЭФР с теоретической
cells.append(nbf.v4.new_markdown_cell(
    "## ЭФР и теоретическая F с грубыми оценками μ̂, b̂"
))
cells.append(nbf.v4.new_code_cell(
    "logs = [math.log(v) for v in sample]\n"
    "mu_hat = s_mean(logs)\n"
    "b_hat = math.sqrt(s_var_unbiased(logs) / 2)\n"
    "print(f'mu_hat = {mu_hat:.6f}, b_hat = {b_hat:.6f}, exp(mu_hat) = {math.exp(mu_hat):.6f}')\n"
    "\n"
    "xs, fs = ecdf(sample)\n"
    "pad = (max(xs) - min(xs)) * 0.05\n"
    "fig, ax = plt.subplots(figsize=(10, 6))\n"
    "ax.step([min(xs) - pad] + xs, [0.0] + fs, where='post', lw=1.4,\n"
    "        color='C0', alpha=0.85, label='$F_n(x)$ (ЭФР)')\n"
    "grid = np.linspace(min(xs) - pad, max(xs) + pad, 600)\n"
    "ax.plot(grid, [loglaplace_cdf(x, mu_hat, b_hat) for x in grid],\n"
    "        lw=1.8, color='C3',\n"
    "        label=fr'$F(x;\\hat\\mu={mu_hat:.4f},\\,\\hat b={b_hat:.4f})$')\n"
    "ax.set(xlabel='x', ylabel='F(x)',\n"
    "       title='ЭФР и теоретическая F(x; μ̂, b̂)')\n"
    "ax.grid(True, ls='--', alpha=0.5); ax.legend(loc='lower right')\n"
    "plt.tight_layout(); plt.show()"
))

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3"},
}

out = ROOT / "TViMS_Coursework.ipynb"
with open(out, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print(f"Saved: {out}")
