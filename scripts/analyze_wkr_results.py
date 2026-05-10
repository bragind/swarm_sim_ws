#!/usr/bin/env python3
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


METRICS = ['connectivity_coeff_mean', 'collisions_count', 'total_energy_wh', 'avg_latency_ms', 'coverage_ratio']
BASELINES = ['central_a_star', 'reactive', 'rule_dec']
PROOF_VALID = ['valid_success', 'valid_completed', 'valid_failure']


def bootstrap_ci(values, reps=3000, alpha=0.05, seed=123):
    vals = np.asarray(pd.to_numeric(pd.Series(values), errors='coerce').dropna(), dtype=float)
    if len(vals) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    samples = rng.choice(vals, size=(reps, len(vals)), replace=True).mean(axis=1)
    return vals.mean(), np.quantile(samples, alpha / 2), np.quantile(samples, 1 - alpha / 2)


def wilson(successes, n, z=1.959963984540054):
    if n == 0:
        return np.nan, np.nan, np.nan
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return p, max(0.0, center - half), min(1.0, center + half)


def cliffs_delta(x, y):
    x = np.asarray(pd.to_numeric(pd.Series(x), errors='coerce').dropna(), dtype=float)
    y = np.asarray(pd.to_numeric(pd.Series(y), errors='coerce').dropna(), dtype=float)
    if len(x) == 0 or len(y) == 0:
        return np.nan
    gt = sum(float(a > b) for a in x for b in y)
    lt = sum(float(a < b) for a in x for b in y)
    return (gt - lt) / (len(x) * len(y))


def bootstrap_diff_p(x, y, reps=3000, seed=321):
    x = np.asarray(pd.to_numeric(pd.Series(x), errors='coerce').dropna(), dtype=float)
    y = np.asarray(pd.to_numeric(pd.Series(y), errors='coerce').dropna(), dtype=float)
    if len(x) == 0 or len(y) == 0:
        return np.nan, np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    diffs = rng.choice(x, (reps, len(x)), True).mean(axis=1) - rng.choice(y, (reps, len(y)), True).mean(axis=1)
    observed = x.mean() - y.mean()
    p = 2 * min(np.mean(diffs <= 0), np.mean(diffs >= 0))
    return observed, np.quantile(diffs, 0.025), np.quantile(diffs, 0.975), min(1.0, p)


def bootstrap_mean_diff(x, y, reps=3000, seed=321):
    diff, _, _, p = bootstrap_diff_p(x, y, reps=reps, seed=seed)
    return diff, p


def holm_bonferroni(pvals):
    valid = [(i, p) for i, p in enumerate(pvals) if not np.isnan(p)]
    ordered = sorted(valid, key=lambda t: t[1])
    adjusted = [np.nan] * len(pvals)
    running = 0.0
    m = len(ordered)
    for rank, (idx, p) in enumerate(ordered):
        running = max(running, (m - rank) * p)
        adjusted[idx] = min(1.0, running)
    return adjusted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--profile', choices=['quick', 'full'], default='full')
    parser.add_argument('--proof-mode', action='store_true')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.input)
    if 'architecture_effective' not in df.columns:
        df['architecture_effective'] = df.get('architecture', '')
    if 'experiment_profile' not in df.columns:
        df['experiment_profile'] = args.profile
    df['success_flag'] = pd.to_numeric(df['success_flag'], errors='coerce').fillna(0)
    valid = df[df['validity_class'].isin(PROOF_VALID)].copy()

    rows = []
    for (scenario, arch), completed in valid.groupby(['scenario_id', 'architecture_effective']):
        successes = int(pd.to_numeric(completed['success_flag'], errors='coerce').fillna(0).sum())
        p, lo, hi = wilson(successes, len(completed))
        row = {
            'scenario_id': scenario,
            'architecture_effective': arch,
            'n': len(completed),
            'success_rate': p,
            'success_rate_ci_low': lo,
            'success_rate_ci_high': hi,
        }
        metric_names = {
            'coverage_ratio': 'coverage',
            'connectivity_coeff_mean': 'connectivity',
            'collisions_count': 'collisions',
            'total_energy_wh': 'energy',
            'avg_latency_ms': 'latency',
        }
        for metric, label in metric_names.items():
            mean, low, high = bootstrap_ci(completed[metric] if metric in completed.columns else [])
            row[f'{label}_mean'] = mean
            row[f'{label}_ci_low'] = low
            row[f'{label}_ci_high'] = high
        rows.append(row)
    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary = summary.sort_values(['scenario_id', 'architecture_effective'])
    summary.to_csv(out / 'summary_by_scenario_architecture.csv', index=False)

    comparisons = []
    for scenario in sorted(valid['scenario_id'].dropna().unique()):
        marl_rows = valid[(valid['scenario_id'] == scenario) & (valid['architecture_effective'] == 'marl_decpomdp')]
        if marl_rows.empty:
            continue
        pvals = []
        pending = []
        marl_success = pd.to_numeric(marl_rows['success_flag'], errors='coerce').fillna(0)
        for base in BASELINES:
            base_rows = valid[(valid['scenario_id'] == scenario) & (valid['architecture_effective'] == base)]
            if base_rows.empty:
                continue
            base_success = pd.to_numeric(base_rows['success_flag'], errors='coerce').fillna(0)
            delta_success, p = bootstrap_mean_diff(marl_success, base_success)
            pvals.append(p)
            pending.append({
                'scenario_id': scenario,
                'baseline': base,
                'delta_success_rate': delta_success,
                'delta_connectivity': bootstrap_mean_diff(marl_rows['connectivity_coeff_mean'], base_rows['connectivity_coeff_mean'])[0],
                'delta_coverage': bootstrap_mean_diff(marl_rows['coverage_ratio'], base_rows['coverage_ratio'])[0],
                'delta_collisions': bootstrap_mean_diff(marl_rows['collisions_count'], base_rows['collisions_count'])[0],
                'delta_energy': bootstrap_mean_diff(marl_rows['total_energy_wh'], base_rows['total_energy_wh'])[0],
                'p_value': p,
                'effect_size': cliffs_delta(marl_success, base_success),
            })
        for row, p_adj in zip(pending, holm_bonferroni(pvals)):
            row['p_value_corrected'] = p_adj
            comparisons.append(row)
    cmp_df = pd.DataFrame(comparisons)
    if cmp_df.empty:
        cmp_df = pd.DataFrame([{'message': 'No proof-valid MARL rows available. MARL superiority cannot be evaluated.'}])
    cmp_df.to_csv(out / 'marl_vs_baselines.csv', index=False)
    df[~df['validity_class'].isin(PROOF_VALID)].to_csv(out / 'invalid_or_timeout_runs.csv', index=False)
    print(f'Analysis written to {out}')
    if comparisons == []:
        print('No proof-valid MARL rows available. MARL superiority cannot be evaluated.')


if __name__ == '__main__':
    main()
