#!/usr/bin/env python3
"""Diagnostics for WKR full diagnostic CSV outputs."""
import argparse
from pathlib import Path

import pandas as pd


PROOF_VALID = {'valid_success', 'valid_completed', 'valid_failure'}


def bool_series(df, column):
    if column not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    return df[column].astype(str).str.lower().isin({'1', 'true', 'yes'})


def grouped_metric(df, metric):
    return (
        df.groupby(['scenario_id', 'architecture_effective'])[metric]
        .agg(['count', 'mean', 'min', 'max'])
        .reset_index()
        .rename(columns={'count': 'n', 'mean': f'{metric}_mean', 'min': f'{metric}_min', 'max': f'{metric}_max'})
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.input)
    if 'architecture_effective' not in df.columns:
        df['architecture_effective'] = df.get('architecture', '')

    for col in ['coverage_ratio', 'connectivity_coeff_mean', 'success_flag', 'timeout_flag', 'runner_timeout_reached']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    valid = df[df['validity_class'].isin(PROOF_VALID)].copy()
    summary = (
        df.groupby(['scenario_id', 'architecture_effective', 'validity_class'])
        .size()
        .reset_index(name='n')
        .sort_values(['scenario_id', 'architecture_effective', 'validity_class'])
    )
    summary.to_csv(out / 'full_failure_summary.csv', index=False)

    grouped_metric(df, 'coverage_ratio').to_csv(out / 'coverage_by_scenario_architecture.csv', index=False)
    grouped_metric(df, 'connectivity_coeff_mean').to_csv(out / 'connectivity_by_scenario_architecture.csv', index=False)

    timeout_cols = {
        'mission_timeout_reached': bool_series(df, 'mission_timeout_reached'),
        'runner_timeout_reached': bool_series(df, 'runner_timeout_reached'),
        'scenario_completed': bool_series(df, 'scenario_completed'),
    }
    timeout_df = pd.DataFrame(timeout_cols)
    timeout_df['complete_reason'] = df.get('complete_reason', '')
    timeout_summary = timeout_df.groupby(['complete_reason', 'mission_timeout_reached', 'runner_timeout_reached', 'scenario_completed']).size().reset_index(name='n')
    timeout_summary.to_csv(out / 'timeout_reason_summary.csv', index=False)

    valid_success = int((df['validity_class'] == 'valid_success').sum())
    valid_failure = int((df['validity_class'] == 'valid_failure').sum())
    runner_timeout = int(bool_series(df, 'runner_timeout_reached').sum())
    diagnostic = int(df['validity_class'].astype(str).str.startswith('diagnostic').sum())
    incomplete = int((df['validity_class'] == 'incomplete_or_timeout').sum())
    mean_cov = float(pd.to_numeric(df['coverage_ratio'], errors='coerce').mean())
    max_cov = float(pd.to_numeric(df['coverage_ratio'], errors='coerce').max())
    mean_conn = float(pd.to_numeric(df['connectivity_coeff_mean'], errors='coerce').mean())
    usable = diagnostic == 0 and incomplete == 0 and runner_timeout == 0 and len(valid) == len(df) and valid_success > 0 and valid_failure > 0

    lines = [
        '# Full Diagnostic Recommendations',
        '',
        f'- Rows: {len(df)}',
        f'- valid_success: {valid_success}',
        f'- valid_failure: {valid_failure}',
        f'- diagnostic rows: {diagnostic}',
        f'- incomplete_or_timeout: {incomplete}',
        f'- runner_timeout: {runner_timeout}',
        f'- mean coverage_ratio: {mean_cov:.4f}',
        f'- max coverage_ratio: {max_cov:.4f}',
        f'- mean connectivity_coeff_mean: {mean_conn:.4f}',
        '',
        '## Chapter 4 usability',
        '',
    ]
    if usable:
        lines.append('The dataset is usable for chapter 4 full diagnostic analysis without trained MARL policy.')
    else:
        lines.append('The dataset needs caution or rerun before chapter 4 claims. Check success/failure balance, diagnostic rows, and runner timeouts.')
    lines.extend([
        '',
        'Use these results for baseline and Dec-POMDP heuristic comparison only. Do not claim proof-valid MARL superiority without a trained `models/marl/wkr_qmix_policy.pt` checkpoint.',
    ])
    (out / 'recommendations.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Diagnostics written to {out}')


if __name__ == '__main__':
    main()
