#!/usr/bin/env python3
import argparse
import csv
import math
import re
import sys
from collections import Counter


PROOF_VALID = {'valid_completed', 'valid_success', 'valid_failure'}
NON_PROOF = {
    'incomplete_or_timeout',
    'diagnostic_marl_model_missing',
    'diagnostic_test_marl_model',
    'diagnostic_metric_accumulation',
    'diagnostic_config_mismatch',
}
REQUIRED = [
    'run_id', 'scenario_id', 'architecture_effective',
    'seed', 'num_agents', 'coverage_ratio', 'connectivity_coeff_mean',
    'collisions_count', 'total_energy_wh', 'validity_class'
]


def f(row, key):
    try:
        return float(row[key])
    except Exception:
        return float('nan')


def truth(row, key):
    return str(row.get(key, '')).strip().lower() in {'1', 'true', 'yes'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--profile', choices=['quick', 'full'], default='full')
    parser.add_argument('--proof-mode', action='store_true')
    args = parser.parse_args()

    with open(args.input, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh))
    errors = []
    counts = Counter(r.get('run_id') for r in rows)
    for run_id, count in counts.items():
        if count != 1:
            errors.append(f'run_id {run_id} has {count} final rows')

    for i, row in enumerate(rows, start=2):
        for key in REQUIRED:
            if row.get(key) in (None, '', 'nan', 'NaN'):
                errors.append(f'line {i}: missing required {key}')
        sid = row.get('scenario_id', '')
        if sid and row.get('run_id') and not re.search(rf'(^|_){re.escape(sid)}(_|$)', row['run_id']):
            errors.append(f'line {i}: scenario_id {sid} does not match run_id {row["run_id"]}')
        if row.get('seed') in ('', 'None', None):
            errors.append(f'line {i}: seed is empty')
        if not (row.get('architecture_requested') or row.get('architecture')):
            errors.append(f'line {i}: missing required architecture_requested/architecture')
        if args.profile == 'full' and row.get('num_agents') and int(float(row['num_agents'])) != 8:
            errors.append(f'line {i}: num_agents is not 8')

        coverage = f(row, 'coverage_ratio')
        conn = f(row, 'connectivity_coeff_mean')
        energy = f(row, 'total_energy_wh')
        collisions = f(row, 'collisions_count')
        if not (0.0 <= coverage <= 1.0):
            errors.append(f'line {i}: coverage_ratio out of [0,1]')
        if not (0.0 <= conn <= 1.0):
            errors.append(f'line {i}: connectivity_coeff_mean out of [0,1]')
        if math.isnan(energy) or energy < 0:
            errors.append(f'line {i}: energy is invalid')
        if math.isnan(collisions) or collisions < 0:
            errors.append(f'line {i}: collisions is invalid')

        validity = row.get('validity_class', '')
        if validity == 'incomplete_or_timeout':
            errors.append(f'line {i}: incomplete_or_timeout is not a completed final result')
        if truth(row, 'runner_timeout_reached') and validity in PROOF_VALID:
            errors.append(f'line {i}: runner_timeout_reached cannot be proof-valid')
        if row.get('scenario_completed') not in (None, '') and not truth(row, 'scenario_completed') and validity in PROOF_VALID:
            errors.append(f'line {i}: proof-valid row has scenario_completed=false')
        if validity.startswith('diagnostic') and validity not in NON_PROOF:
            errors.append(f'line {i}: unknown diagnostic validity_class {validity}')
        requested_arch = row.get('architecture_requested') or row.get('architecture')
        if requested_arch == 'marl_decpomdp' and validity in PROOF_VALID and not truth(row, 'marl_model_loaded'):
            errors.append(f'line {i}: proof-valid marl_decpomdp without loaded MARL model')
        if args.proof_mode and requested_arch == 'marl_decpomdp':
            if not truth(row, 'marl_model_loaded'):
                errors.append(f'line {i}: proof marl_decpomdp without loaded MARL model')
            if not truth(row, 'marl_model_allowed_for_proof'):
                errors.append(f'line {i}: proof marl_decpomdp without proof-allowed MARL model')
            if validity not in PROOF_VALID:
                errors.append(f'line {i}: proof marl_decpomdp has non-proof validity_class {validity}')

    if errors:
        print('\n'.join(errors))
        return 1
    completed_rows = sum(1 for r in rows if r.get('validity_class') in PROOF_VALID)
    label = 'proof-valid' if args.proof_mode else 'completed-valid'
    print(f'Validation passed: {len(rows)} final rows, {completed_rows} {label} rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
