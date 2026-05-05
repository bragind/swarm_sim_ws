import csv
import subprocess
import sys
from pathlib import Path


FIELDS = [
    'run_id', 'scenario_id', 'architecture', 'architecture_effective', 'seed',
    'num_agents', 'num_uavs', 'num_ugvs', 'start_time', 'end_time',
    'mission_time_s', 'mission_timeout_s', 'success_flag', 'timeout_flag',
    'complete_reason', 'collisions_count', 'total_energy_wh', 'avg_latency_ms',
    'packet_loss_ratio', 'connectivity_coeff_mean', 'connectivity_coeff_min',
    'coverage_ratio', 'agents_failed_count', 'marl_model_loaded', 'validity_class'
]


def write_csv(path: Path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def valid_row(run_id='S1_reactive_seed43_test', scenario='S1', arch='reactive', seed=43):
    return {
        'run_id': run_id,
        'scenario_id': scenario,
        'architecture': arch,
        'architecture_effective': arch,
        'seed': seed,
        'num_agents': 8,
        'num_uavs': 5,
        'num_ugvs': 3,
        'start_time': 1,
        'end_time': 2,
        'mission_time_s': 1,
        'mission_timeout_s': 120,
        'success_flag': 1,
        'timeout_flag': 0,
        'complete_reason': 'mission_success',
        'collisions_count': 0,
        'total_energy_wh': 0.1,
        'avg_latency_ms': 20,
        'packet_loss_ratio': 0,
        'connectivity_coeff_mean': 0.8,
        'connectivity_coeff_min': 0.7,
        'coverage_ratio': 0.8,
        'agents_failed_count': 0,
        'marl_model_loaded': 'true' if arch == 'marl_decpomdp' else 'false',
        'validity_class': 'valid_success',
    }


def run_validate(path):
    return subprocess.run([sys.executable, 'scripts/validate_results.py', '--input', str(path)], text=True, capture_output=True)


def test_final_metrics_one_row_per_run(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    row = valid_row()
    write_csv(path, [row, row])
    assert run_validate(path).returncode != 0


def test_scenario_id_propagation(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    write_csv(path, [valid_row(run_id='S2_reactive_seed43_test', scenario='S1')])
    assert run_validate(path).returncode != 0


def test_architecture_propagation(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    row = valid_row()
    row['architecture'] = ''
    write_csv(path, [row])
    assert run_validate(path).returncode != 0


def test_seed_propagation(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    row = valid_row()
    row['seed'] = ''
    write_csv(path, [row])
    assert run_validate(path).returncode != 0


def test_coverage_ratio_range_0_1(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    row = valid_row()
    row['coverage_ratio'] = 1.2
    write_csv(path, [row])
    assert run_validate(path).returncode != 0


def test_connectivity_range_0_1(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    row = valid_row()
    row['connectivity_coeff_mean'] = -0.1
    write_csv(path, [row])
    assert run_validate(path).returncode != 0


def test_marl_model_required_for_marl_architecture(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    row = valid_row(run_id='S1_marl_decpomdp_seed43_test', arch='marl_decpomdp')
    row['marl_model_loaded'] = 'false'
    write_csv(path, [row])
    assert run_validate(path).returncode != 0


def test_metrics_reset_between_runs(tmp_path):
    path = tmp_path / 'final_metrics.csv'
    write_csv(path, [
        valid_row(run_id='S1_reactive_seed43_a', seed=43),
        valid_row(run_id='S1_reactive_seed44_b', seed=44),
    ])
    assert run_validate(path).returncode == 0
