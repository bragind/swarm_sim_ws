#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


BASE_ARCHS = ['central_a_star', 'reactive', 'rule_dec', 'decpomdp_heuristic']
MARL_ARCH = 'marl_decpomdp'
SCENARIOS = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']
PROOF_VALID = {'valid_success', 'valid_completed', 'valid_failure'}

ARCH_LABELS = {
    'central_a_star': 'Централизованное планирование (Central-A*)',
    'reactive': 'Реактивное управление',
    'rule_dec': 'Децентрализованный rule-based алгоритм',
    'decpomdp_heuristic': 'Предложенная архитектура (Dec-POMDP + эвристическая коррекция)',
    'marl_decpomdp': 'MARL + Dec-POMDP',
}
ARCH_COLORS = {
    'central_a_star': '#4C78A8',
    'reactive': '#F58518',
    'rule_dec': '#54A24B',
    'decpomdp_heuristic': '#B279A2',
    'marl_decpomdp': '#E45756',
}
PLOT_TITLES = {
    'success': 'Сравнение успешности выполнения миссии',
    'connectivity': 'Сравнение коэффициента сохранения связности роя',
    'coverage': 'Сравнение коэффициента покрытия территории',
    'collisions': 'Сравнение числа столкновений в различных сценариях',
    'energy': 'Сравнение суммарного энергопотребления',
    'integral': 'Сравнение интегрального показателя эффективности',
}
SUBTITLE = 'Полная диагностическая серия имитационных экспериментов'


def setup_matplotlib():
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['legend.fontsize'] = 9


def truth(series):
    return series.astype(str).str.lower().isin({'1', 'true', 'yes'})


def architecture_order(df, proof_mode=False):
    archs = [arch for arch in BASE_ARCHS if arch in set(df['architecture_effective'])]
    if proof_mode and MARL_ARCH in set(df['architecture_effective']):
        marl = df[
            (df['architecture_effective'] == MARL_ARCH)
            & (df['validity_class'].isin(PROOF_VALID))
            & truth(df.get('marl_model_loaded', pd.Series('', index=df.index)))
            & truth(df.get('marl_model_allowed_for_proof', pd.Series('', index=df.index)))
        ]
        if not marl.empty:
            archs.append(MARL_ARCH)
    return archs


def bootstrap_ci(values, reps=2000, seed=99):
    vals = np.asarray(pd.to_numeric(pd.Series(values), errors='coerce').dropna(), dtype=float)
    if len(vals) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    samples = rng.choice(vals, size=(reps, len(vals)), replace=True).mean(axis=1)
    return vals.mean(), np.quantile(samples, 0.025), np.quantile(samples, 0.975)


def finish(fig, ax, output, title_key):
    ax.set_title(PLOT_TITLES[title_key] + '\n' + SUBTITLE, pad=14)
    ax.set_xlabel('Сценарии эксперимента')
    ax.grid(axis='y', alpha=0.25)
    fig.tight_layout(rect=[0.02, 0.12, 0.98, 0.98])
    fig.savefig(output.with_suffix('.svg'))
    fig.savefig(output.with_suffix('.png'), dpi=220)
    plt.close(fig)


def legend_bottom(fig, handles):
    fig.legend(
        handles=handles,
        loc='lower center',
        bbox_to_anchor=(0.5, 0.01),
        ncol=2,
        frameon=False,
    )


def grouped_metric(df, archs, metric, ylabel, output, title_key, percent=False):
    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    x = np.arange(len(SCENARIOS))
    width = min(0.18, 0.82 / max(1, len(archs)))
    handles = []
    for idx, arch in enumerate(archs):
        means, lows, highs = [], [], []
        for scenario in SCENARIOS:
            vals = df[(df.scenario_id == scenario) & (df.architecture_effective == arch)][metric]
            mean, low, high = bootstrap_ci(vals)
            scale = 100.0 if percent else 1.0
            means.append(mean * scale)
            lows.append(max(0.0, (mean - low) * scale) if not np.isnan(mean) else 0.0)
            highs.append(max(0.0, (high - mean) * scale) if not np.isnan(mean) else 0.0)
        positions = x + (idx - (len(archs) - 1) / 2) * width
        ax.bar(positions, means, width, color=ARCH_COLORS[arch], yerr=[lows, highs], capsize=3)
        handles.append(Patch(facecolor=ARCH_COLORS[arch], label=ARCH_LABELS[arch]))
    ax.set_xticks(x)
    ax.set_xticklabels(SCENARIOS)
    ax.set_ylabel(ylabel)
    legend_bottom(fig, handles)
    finish(fig, ax, output, title_key)


def success_plot(df, archs, output):
    work = df.assign(success_rate=pd.to_numeric(df.success_flag, errors='coerce'))
    grouped_metric(work, archs, 'success_rate', 'Успешность выполнения миссии, %', output, 'success', percent=True)


def boxplot(df, archs, metric, ylabel, output, title_key):
    fig, ax = plt.subplots(figsize=(14, 7.4))
    data, positions, colors = [], [], []
    pos = 1
    for scenario in SCENARIOS:
        for arch in archs:
            vals = pd.to_numeric(
                df[(df.scenario_id == scenario) & (df.architecture_effective == arch)][metric],
                errors='coerce',
            ).dropna()
            data.append(vals)
            positions.append(pos)
            colors.append(ARCH_COLORS[arch])
            pos += 1
        pos += 1
    box = ax.boxplot(data, positions=positions, widths=0.65, patch_artist=True, showfliers=False)
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.78)
    centers = [np.mean(positions[i * len(archs):(i + 1) * len(archs)]) for i in range(len(SCENARIOS))]
    ax.set_xticks(centers)
    ax.set_xticklabels(SCENARIOS)
    ax.set_ylabel(ylabel)
    legend_bottom(fig, [Patch(facecolor=ARCH_COLORS[arch], label=ARCH_LABELS[arch]) for arch in archs])
    finish(fig, ax, output, title_key)


def integral_scores(df, archs):
    rows = []
    for scenario in SCENARIOS:
        sub = df[df.scenario_id == scenario].copy()
        if sub.empty:
            continue
        agg = sub.groupby('architecture_effective').agg(
            success_rate=('success_flag', 'mean'),
            connectivity=('connectivity_coeff_mean', 'mean'),
            coverage=('coverage_ratio', 'mean'),
            collisions=('collisions_count', 'mean'),
            energy=('total_energy_wh', 'mean'),
        ).reindex(archs)
        for col in ['connectivity', 'coverage']:
            agg[col + '_norm'] = agg[col].astype(float).clip(0, 1)
        for col in ['collisions', 'energy']:
            vals = agg[col].astype(float)
            span = vals.max() - vals.min()
            agg[col + '_norm'] = 0.0 if span == 0 or np.isnan(span) else (vals - vals.min()) / span
        agg['J'] = (
            0.30 * agg['success_rate']
            + 0.25 * agg['connectivity_norm']
            + 0.20 * agg['coverage_norm']
            + 0.15 * (1 - agg['collisions_norm'])
            + 0.10 * (1 - agg['energy_norm'])
        )
        for arch, row in agg.iterrows():
            rows.append({'scenario_id': scenario, 'architecture_effective': arch, 'J': row['J']})
    return pd.DataFrame(rows)


def integral_score_plot(df, archs, output):
    score = integral_scores(df, archs)
    grouped_metric(score, archs, 'J', 'Интегральный показатель', output, 'integral')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--profile', choices=['quick', 'full'], default='full')
    parser.add_argument('--proof-mode', action='store_true')
    args = parser.parse_args()

    setup_matplotlib()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.input)
    if 'architecture_effective' not in df.columns:
        df['architecture_effective'] = df.get('architecture', '')
    valid = df[df.validity_class.isin(PROOF_VALID)].copy()
    archs = architecture_order(valid, proof_mode=args.proof_mode)
    valid = valid[valid['architecture_effective'].isin(archs)].copy()
    for col in ['success_flag', 'connectivity_coeff_mean', 'coverage_ratio', 'collisions_count', 'total_energy_wh']:
        valid[col] = pd.to_numeric(valid[col], errors='coerce')

    optional_out = out / 'optional'
    optional_out.mkdir(parents=True, exist_ok=True)
    success_plot(valid, archs, optional_out / 'fig_success_rate_by_architecture')
    grouped_metric(valid, archs, 'connectivity_coeff_mean', 'Коэффициент связности', out / 'fig_connectivity_by_architecture', 'connectivity')
    grouped_metric(valid, archs, 'coverage_ratio', 'Коэффициент покрытия', out / 'fig_coverage_by_architecture', 'coverage')
    boxplot(valid, archs, 'collisions_count', 'Число столкновений', out / 'fig_collisions_boxplot', 'collisions')
    boxplot(valid, archs, 'total_energy_wh', 'Энергопотребление, Вт·ч', out / 'fig_energy_boxplot', 'energy')
    integral_score_plot(valid, archs, out / 'fig_integral_score')
    print(f'Figures written to {out}')


if __name__ == '__main__':
    main()
