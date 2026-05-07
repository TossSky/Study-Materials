# -*- coding: utf-8 -*-
"""Расчётный модуль курсовой работы по ТВиМС, вариант 9 (Log-Laplace).
Запуск:  python compute.py
Выход:   PNG-графики + numbers.json (числовые результаты для отчёта).
"""

import csv
import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)
SEED = 20260507
RNG = np.random.default_rng(SEED)


# ---------- Чтение выборки (стандартными средствами Python) ----------
def read_sample(path):
    sample = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            sample.append(float(row[0]))
    return sample


# ---------- 2. Функции для вычисления статистик (без numpy/scipy) ----------
def s_sum(x):
    s = 0.0
    for v in x:
        s += v
    return s


def s_mean(x):
    return s_sum(x) / len(x)


def s_median(x):
    n = len(x)
    s = sorted(x)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def s_mode(x, decimals=3):
    """Мода для непрерывной выборки определяется по округлённым значениям
    (без округления у непрерывной выборки моды нет — все значения уникальны).
    """
    counts = {}
    for v in x:
        key = round(v, decimals)
        counts[key] = counts.get(key, 0) + 1
    max_cnt = 0
    mode_keys = []
    for k, c in counts.items():
        if c > max_cnt:
            max_cnt = c
            mode_keys = [k]
        elif c == max_cnt:
            mode_keys.append(k)
    return mode_keys, max_cnt


def s_range(x):
    return max(x) - min(x)


def s_var_biased(x):
    m = s_mean(x)
    s = 0.0
    for v in x:
        s += (v - m) ** 2
    return s / len(x)


def s_var_unbiased(x):
    m = s_mean(x)
    s = 0.0
    for v in x:
        s += (v - m) ** 2
    return s / (len(x) - 1)


def s_initial_moment(x, k):
    s = 0.0
    for v in x:
        s += v ** k
    return s / len(x)


def s_central_moment(x, k):
    m = s_mean(x)
    s = 0.0
    for v in x:
        s += (v - m) ** k
    return s / len(x)


# ---------- 3. Эмпирическая функция распределения (без statsmodels) ----------
def ecdf(sample):
    """Возвращает (xs, fs) — точки разрыва и значения F_n(x_(i)).
    F_n(x) = (число элементов выборки <= x) / n.
    """
    s = sorted(sample)
    n = len(s)
    fs = [(i + 1) / n for i in range(n)]
    return s, fs


def plot_ecdf(sample, label, out_path):
    xs, fs = ecdf(sample)
    n = len(sample)
    fig, ax = plt.subplots(figsize=(8, 5))
    pad = (max(xs) - min(xs)) * 0.05 if max(xs) > min(xs) else 0.05
    x_left = [min(xs) - pad] + xs
    f_left = [0.0] + fs
    ax.step(x_left, f_left, where="post", linewidth=1.6, label=f"$F_n(x)$, n = {n}")
    ax.scatter(xs, fs, s=14, zorder=3, color="C0")
    ax.set_xlabel("x")
    ax.set_ylabel("$F_n(x)$")
    ax.set_title(f"Эмпирическая функция распределения: {label}")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_ylim(-0.02, 1.02)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


# ---------- 4. Гистограмма (без numpy.histogram) ----------
def histogram(sample, bins=None):
    """Группирует выборку по равноширинным интервалам.
    Если число интервалов не задано — формула Стёрджеса k = 1 + log2(n).
    Возвращает edges (k+1 точек) и плотность h_i = n_i / (n * dx).
    """
    n = len(sample)
    if bins is None:
        bins = max(1, int(round(1 + math.log2(n))))
    a, b = min(sample), max(sample)
    if a == b:
        b = a + 1.0
    edges = [a + (b - a) * i / bins for i in range(bins + 1)]
    counts = [0] * bins
    for v in sample:
        # последний интервал — закрытый справа
        idx = int((v - a) / (b - a) * bins)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1
    dx = (b - a) / bins
    density = [c / (n * dx) for c in counts]
    return edges, counts, density


def plot_histogram(sample, label, out_path):
    edges, counts, dens = histogram(sample)
    fig, ax = plt.subplots(figsize=(8, 5))
    widths = [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
    ax.bar(centers, dens, width=widths, edgecolor="black",
           color="#4C72B0", alpha=0.75,
           label=f"гистограмма, n = {len(sample)}")
    ax.set_xlabel("x")
    ax.set_ylabel("плотность")
    ax.set_title(f"Гистограмма выборки: {label}")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


# ---------- 5. Теоретическая функция распределения Log-Laplace ----------
def loglaplace_pdf(x, mu, b):
    """f(x) = 1/(2 b x) * exp(-|ln x - mu| / b), x > 0."""
    if x <= 0:
        return 0.0
    return math.exp(-abs(math.log(x) - mu) / b) / (2 * b * x)


def loglaplace_cdf(x, mu, b):
    """Кусочно-заданная CDF.
    F(x) = 0,                                    x <= 0
         = 0.5 * exp((ln x - mu)/b),             0 < x <= e^mu
         = 1 - 0.5 * exp(-(ln x - mu)/b),        x  > e^mu
    """
    if x <= 0:
        return 0.0
    z = math.log(x) - mu
    if z <= 0:
        return 0.5 * math.exp(z / b)
    return 1.0 - 0.5 * math.exp(-z / b)


def plot_loglaplace_examples(out_path):
    """График F(x; mu, b) для нескольких сочетаний параметров."""
    fig, ax = plt.subplots(figsize=(8, 5))
    presets = [
        (1.971, 0.018, "C0"),
        (1.971, 0.040, "C1"),
        (1.971, 0.005, "C2"),
        (2.500, 0.018, "C3"),
        (1.500, 0.018, "C4"),
    ]
    x_grid = np.linspace(3.5, 13.0, 800)
    for mu, b, c in presets:
        F = [loglaplace_cdf(xx, mu, b) for xx in x_grid]
        ax.plot(x_grid, F, color=c, linewidth=1.7,
                label=fr"$\mu={mu:.3f}$, $b={b:.3f}$")
    ax.set_xlabel("x")
    ax.set_ylabel("F(x; μ, b)")
    ax.set_title("Теоретическая функция распределения Log-Laplace")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_param_influence(out_path):
    """Влияние каждого параметра при фиксации другого."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    x_grid = np.linspace(3.5, 13.0, 800)

    # 1) Фиксируем b, меняем mu
    for mu, c in [(1.50, "C0"), (2.20, "C1")]:
        F = [loglaplace_cdf(xx, mu, 0.05) for xx in x_grid]
        axes[0].plot(x_grid, F, color=c, linewidth=1.8,
                     label=fr"$\mu={mu:.2f}$, $b=0.05$")
    axes[0].set_title("Влияние параметра μ (b = 0.05)")
    axes[0].set_xlabel("x"); axes[0].set_ylabel("F(x)")
    axes[0].grid(True, linestyle="--", alpha=0.5); axes[0].legend()

    # 2) Фиксируем mu, меняем b
    for b, c in [(0.01, "C0"), (0.10, "C1")]:
        F = [loglaplace_cdf(xx, 1.97, b) for xx in x_grid]
        axes[1].plot(x_grid, F, color=c, linewidth=1.8,
                     label=fr"$\mu=1.97$, $b={b:.2f}$")
    axes[1].set_title("Влияние параметра b (μ = 1.97)")
    axes[1].set_xlabel("x"); axes[1].set_ylabel("F(x)")
    axes[1].grid(True, linestyle="--", alpha=0.5); axes[1].legend()

    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


# ---------- Сравнение ЭФР с теоретической ----------
def plot_ecdf_vs_theory(sample, mu, b, out_path):
    xs_e, fs_e = ecdf(sample)
    fig, ax = plt.subplots(figsize=(8, 5))
    pad = (max(xs_e) - min(xs_e)) * 0.05
    ax.step([min(xs_e) - pad] + xs_e, [0.0] + fs_e, where="post",
            linewidth=1.4, label="$F_n(x)$ (ЭФР)", color="C0", alpha=0.85)
    x_grid = np.linspace(min(xs_e) - pad, max(xs_e) + pad, 600)
    F = [loglaplace_cdf(xx, mu, b) for xx in x_grid]
    ax.plot(x_grid, F, linewidth=1.8, color="C3",
            label=fr"$F(x;\,\hat\mu={mu:.4f},\,\hat b={b:.4f})$")
    ax.set_xlabel("x"); ax.set_ylabel("F(x)")
    ax.set_title("Сравнение ЭФР и теоретической функции Log-Laplace")
    ax.grid(True, linestyle="--", alpha=0.5); ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


# =================================================================
def main():
    sample = read_sample(ROOT / "var_9_loglaplace.csv")
    n = len(sample)

    # ---- 2. Статистики ----
    res = {
        "n": n,
        "sum": s_sum(sample),
        "mean": s_mean(sample),
        "median": s_median(sample),
        "range": s_range(sample),
        "min": min(sample),
        "max": max(sample),
        "var_biased": s_var_biased(sample),
        "var_unbiased": s_var_unbiased(sample),
        "std_unbiased": math.sqrt(s_var_unbiased(sample)),
        "moment_initial_3": s_initial_moment(sample, 3),
        "moment_initial_4": s_initial_moment(sample, 4),
        "moment_central_3": s_central_moment(sample, 3),
        "moment_central_4": s_central_moment(sample, 4),
    }
    mode_keys, mode_cnt = s_mode(sample, decimals=2)
    res["mode_decimals"] = 2
    res["mode_count"] = mode_cnt
    res["mode_values"] = sorted(mode_keys)[:5]

    # ---- 3. ЭФР: подвыборки 10, 100, 200 ----
    for k in (10, 100, 200):
        idx = RNG.choice(n, size=k, replace=False)
        sub = [sample[i] for i in idx]
        plot_ecdf(sub, f"подвыборка n = {k}", FIG_DIR / f"ecdf_{k}.png")
    plot_ecdf(sample, f"полная выборка n = {n}", FIG_DIR / f"ecdf_full.png")

    # ---- 4. Гистограмма: подвыборки 10, 100, 200 ----
    for k in (10, 100, 200):
        idx = RNG.choice(n, size=k, replace=False)
        sub = [sample[i] for i in idx]
        plot_histogram(sub, f"подвыборка n = {k}", FIG_DIR / f"hist_{k}.png")
    plot_histogram(sample, f"полная выборка n = {n}",
                   FIG_DIR / f"hist_full.png")

    # ---- 5. Теоретическая функция и влияние параметров ----
    # Оценим параметры по выборке (для последующего сравнения):
    logs = [math.log(v) for v in sample]
    mu_hat = s_mean(logs)                        # среднее логарифмов
    b_hat_mom = math.sqrt(s_var_unbiased(logs) / 2.0)   # из var = 2 b^2
    # ML-оценка b в Лапласе: b = (1/n) * сумма |y_i - median|
    med_log = s_median(logs)
    b_hat_mle = sum(abs(yy - med_log) for yy in logs) / len(logs)

    res["mu_hat_mean_logs"] = mu_hat
    res["b_hat_from_var"] = b_hat_mom
    res["median_logs"] = med_log
    res["b_hat_mle"] = b_hat_mle

    plot_loglaplace_examples(FIG_DIR / "loglaplace_examples.png")
    plot_param_influence(FIG_DIR / "loglaplace_param_influence.png")
    plot_ecdf_vs_theory(sample, mu_hat, b_hat_mom,
                        FIG_DIR / "ecdf_vs_theory.png")

    with open(ROOT / "numbers.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("OK. Numbers:")
    for k, v in res.items():
        print(f"  {k} = {v}")


if __name__ == "__main__":
    main()
