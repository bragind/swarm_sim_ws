#!/usr/bin/env python3
"""Export Russian chapter-4 tables from WKR final_metrics.csv."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ARCHS = ['central_a_star', 'reactive', 'rule_dec', 'decpomdp_heuristic']
SCENARIOS = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']
PROOF_VALID = {'valid_success', 'valid_completed', 'valid_failure'}
ARCH_LABELS = {
    'central_a_star': 'Централизованное планирование (Central-A*)',
    'reactive': 'Реактивное управление',
    'rule_dec': 'Децентрализованный rule-based алгоритм',
    'decpomdp_heuristic': 'Предложенная архитектура (Dec-POMDP + эвристическая коррекция)',
}
SCENARIO_DESCRIPTIONS = {
    'S1': 'Номинальная навигация при штатной связи и умеренной плотности препятствий.',
    'S2': 'Плотное препятственное окружение.',
    'S3': 'Деградация связи: потери пакетов и повышенная задержка.',
    'S4': 'Частичный отказ агентов в ходе миссии.',
    'S5': 'Вычислительная деградация и задержка принятия решений.',
    'S6': 'Комбинированный стресс: препятствия, связь, отказы и вычислительная деградация.',
}
SUCCESS_NOTE = (
    'Используется как контрольная метрика работоспособности стенда, '
    'не как основной сравнительный показатель.'
)


def to_markdown(df):
    cols = list(df.columns)
    rows = [[str(value) for value in row] for row in df.astype(str).itertuples(index=False, name=None)]
    widths = []
    for idx, col in enumerate(cols):
        widths.append(max(len(str(col)), *(len(row[idx]) for row in rows)) if rows else len(str(col)))
    header = '| ' + ' | '.join(str(col).ljust(widths[idx]) for idx, col in enumerate(cols)) + ' |'
    sep = '| ' + ' | '.join('-' * widths[idx] for idx in range(len(cols))) + ' |'
    body = ['| ' + ' | '.join(row[idx].ljust(widths[idx]) for idx in range(len(cols))) + ' |' for row in rows]
    return '\n'.join([header, sep] + body)


def save_table(df, out, stem, note=''):
    df.to_csv(out / f'{stem}.csv', index=False, encoding='utf-8-sig')
    text = ''
    if note:
        text += note + '\n\n'
    text += to_markdown(df) + '\n'
    (out / f'{stem}.md').write_text(text, encoding='utf-8')


def truth(series):
    return series.astype(str).str.lower().isin({'1', 'true', 'yes'})


def integral_scores(valid):
    rows = []
    for scenario in SCENARIOS:
        sub = valid[valid['scenario_id'] == scenario].copy()
        if sub.empty:
            continue
        agg = sub.groupby('architecture_effective').agg(
            success_rate=('success_flag', 'mean'),
            coverage=('coverage_ratio', 'mean'),
            connectivity=('connectivity_coeff_mean', 'mean'),
            collisions=('collisions_count', 'mean'),
            energy=('total_energy_wh', 'mean'),
        ).reindex(ARCHS)
        for col in ['coverage', 'connectivity']:
            agg[col + '_norm'] = agg[col].astype(float).clip(0, 1)
        for col in ['collisions', 'energy']:
            vals = agg[col].astype(float)
            span = vals.max() - vals.min()
            agg[col + '_norm'] = 0.0 if span == 0 or np.isnan(span) else (vals - vals.min()) / span
        agg['integral_score'] = (
            0.30 * agg['success_rate']
            + 0.25 * agg['connectivity_norm']
            + 0.20 * agg['coverage_norm']
            + 0.15 * (1 - agg['collisions_norm'])
            + 0.10 * (1 - agg['energy_norm'])
        )
        for arch, row in agg.iterrows():
            rows.append({
                'scenario_id': scenario,
                'architecture_effective': arch,
                'integral_score': row['integral_score'],
            })
    return pd.DataFrame(rows)


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
    df = df[df['architecture_effective'].isin(ARCHS)].copy()
    for col in ['success_flag', 'coverage_ratio', 'connectivity_coeff_mean', 'collisions_count', 'total_energy_wh']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    valid = df[df['validity_class'].isin(PROOF_VALID)].copy()
    scores = integral_scores(valid)

    seed_count = valid['seed'].nunique()
    matrix_rows = []
    for scenario in SCENARIOS:
        runs = len(valid[valid['scenario_id'] == scenario])
        matrix_rows.append({
            'Сценарий': scenario,
            'Описание': SCENARIO_DESCRIPTIONS[scenario],
            'Архитектуры': '; '.join(ARCH_LABELS[a] for a in ARCHS),
            'Количество seed': seed_count,
            'Количество запусков': runs,
        })
    save_table(pd.DataFrame(matrix_rows), out, 'table_4_1_experiment_matrix')

    total = len(df)
    successes = int((df['validity_class'] == 'valid_success').sum())
    success_rate = 100.0 * successes / total if total else 0.0
    validity = pd.DataFrame([
        {'Показатель': 'Всего запусков', 'Значение': total},
        {'Показатель': 'valid_success', 'Значение': successes},
        {'Показатель': 'valid_failure', 'Значение': int((df['validity_class'] == 'valid_failure').sum())},
        {'Показатель': 'diagnostic rows', 'Значение': int(df['validity_class'].astype(str).str.startswith('diagnostic').sum())},
        {'Показатель': 'incomplete_or_timeout', 'Значение': int((df['validity_class'] == 'incomplete_or_timeout').sum())},
        {'Показатель': 'runner_timeout_reached', 'Значение': int(truth(df.get('runner_timeout_reached', pd.Series('', index=df.index))).sum())},
        {'Показатель': 'Общая успешность', 'Значение': f'{success_rate:.1f} %'.replace('.', ',')},
    ])
    save_table(validity, out, 'table_4_2_validity_summary')

    success = valid.groupby(['scenario_id', 'architecture_effective'])['success_flag'].mean().reset_index()
    success['Архитектура'] = success['architecture_effective'].map(ARCH_LABELS)
    success['success_rate, %'] = success['success_flag'].map(lambda v: f'{100.0 * float(v):.1f}'.replace('.', ','))
    success_table = success.pivot(index='scenario_id', columns='Архитектура', values='success_rate, %').reset_index()
    success_table = success_table.rename(columns={'scenario_id': 'Сценарий'})
    save_table(success_table, out, 'table_4_3_success_rate', note=SUCCESS_NOTE)

    metrics = valid.groupby(['scenario_id', 'architecture_effective']).agg(
        coverage_ratio_mean=('coverage_ratio', 'mean'),
        connectivity_coeff_mean=('connectivity_coeff_mean', 'mean'),
        collisions_count_mean=('collisions_count', 'mean'),
        total_energy_wh_mean=('total_energy_wh', 'mean'),
    ).reset_index()
    metrics = metrics.merge(scores, on=['scenario_id', 'architecture_effective'], how='left')
    metrics['Архитектура'] = metrics['architecture_effective'].map(ARCH_LABELS)
    metrics_table = metrics.rename(columns={
        'scenario_id': 'Сценарий',
        'coverage_ratio_mean': 'coverage_ratio mean',
        'connectivity_coeff_mean': 'connectivity_coeff_mean',
        'collisions_count_mean': 'collisions_count mean',
        'total_energy_wh_mean': 'total_energy_wh mean',
        'integral_score': 'integral_score mean',
    })[['Сценарий', 'Архитектура', 'coverage_ratio mean', 'connectivity_coeff_mean', 'collisions_count mean', 'total_energy_wh mean', 'integral_score mean']]
    for col in ['coverage_ratio mean', 'connectivity_coeff_mean', 'collisions_count mean', 'total_energy_wh mean', 'integral_score mean']:
        metrics_table[col] = metrics_table[col].map(lambda x: f'{float(x):.4f}')
    save_table(metrics_table, out, 'table_4_4_mean_metrics')

    merged = metrics.merge(scores, on=['scenario_id', 'architecture_effective'], how='left', suffixes=('', '_score'))
    best_rows = []
    for scenario in SCENARIOS:
        sub = merged[merged['scenario_id'] == scenario].copy()
        best_integral = sub.loc[sub['integral_score'].astype(float).idxmax(), 'architecture_effective']
        best_conn = sub.loc[sub['connectivity_coeff_mean'].astype(float).idxmax(), 'architecture_effective']
        best_energy = sub.loc[sub['total_energy_wh_mean'].astype(float).idxmin(), 'architecture_effective']
        comment = 'Стресс-сценарий выявляет различия между архитектурами.' if scenario == 'S6' else 'Сценарий завершен устойчиво для сравниваемых архитектур.'
        best_rows.append({
            'Сценарий': scenario,
            'Лучшая архитектура по integral_score': ARCH_LABELS[best_integral],
            'Лучшая архитектура по connectivity': ARCH_LABELS[best_conn],
            'Лучшая архитектура по energy': ARCH_LABELS[best_energy],
            'Комментарий': comment,
        })
    save_table(pd.DataFrame(best_rows), out, 'table_4_5_best_architecture_by_scenario')
    print(f'Tables written to {out}')


if __name__ == '__main__':
    main()
