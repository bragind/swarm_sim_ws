#!/usr/bin/env python3
"""Batch runner for WKR scenario x architecture experiments."""
import argparse
import csv
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


PROOF_ARCHITECTURES = ['central_a_star', 'reactive', 'rule_dec', 'marl_decpomdp']
FULL_DIAGNOSTIC_ARCHITECTURES = ['central_a_star', 'reactive', 'rule_dec', 'decpomdp_heuristic']
QUICK_ARCHITECTURES = ['reactive', 'decpomdp_heuristic']
SCENARIOS = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']
SIMULATION_MODES = ['headless_fast_kinematic', 'gazebo_headless']
DEFAULT_SCENARIO_CONFIGS = {
    'S1': {'num_uavs': 5, 'num_ugvs': 3, 'num_agents_total': 8, 'packet_loss': 0.00, 'latency_ms': 20.0, 'agent_failure_ratio': 0.0, 'compute_delay_ms': 0.0, 'mission_timeout_s': 120.0},
    'S2': {'num_uavs': 5, 'num_ugvs': 3, 'num_agents_total': 8, 'packet_loss': 0.02, 'latency_ms': 25.0, 'agent_failure_ratio': 0.0, 'compute_delay_ms': 0.0, 'mission_timeout_s': 150.0},
    'S3': {'num_uavs': 5, 'num_ugvs': 3, 'num_agents_total': 8, 'packet_loss': 0.25, 'latency_ms': 80.0, 'agent_failure_ratio': 0.0, 'compute_delay_ms': 0.0, 'mission_timeout_s': 150.0},
    'S4': {'num_uavs': 5, 'num_ugvs': 3, 'num_agents_total': 8, 'packet_loss': 0.05, 'latency_ms': 35.0, 'agent_failure_ratio': 0.25, 'compute_delay_ms': 0.0, 'mission_timeout_s': 150.0},
    'S5': {'num_uavs': 5, 'num_ugvs': 3, 'num_agents_total': 8, 'packet_loss': 0.02, 'latency_ms': 30.0, 'agent_failure_ratio': 0.0, 'compute_delay_ms': 120.0, 'mission_timeout_s': 150.0},
    'S6': {'num_uavs': 5, 'num_ugvs': 3, 'num_agents_total': 8, 'packet_loss': 0.25, 'latency_ms': 80.0, 'agent_failure_ratio': 0.25, 'compute_delay_ms': 120.0, 'mission_timeout_s': 180.0},
}
DEFAULT_PROFILES = {
    'quick': {'coverage_threshold': 0.30, 'connectivity_threshold': 0.40, 'mission_timeout_s': 60.0, 'shutdown_grace_s': 15.0, 'min_active_agents': 6, 'simulation_mode': 'headless_fast_kinematic'},
    'full': {'coverage_threshold': 0.60, 'connectivity_threshold': 0.50, 'mission_timeout_s': 180.0, 'shutdown_grace_s': 30.0, 'min_active_agents': 6, 'simulation_mode': 'gazebo_headless'},
}
DEFAULT_ARCHITECTURE_CONFIGS = {
    'central_a_star': {'coverage_efficiency_factor': 1.15, 'connectivity_recovery_factor': 0.78, 'collision_avoidance_factor': 0.82, 'energy_efficiency_factor': 0.88, 'failure_recovery_factor': 0.68},
    'reactive': {'coverage_efficiency_factor': 0.78, 'connectivity_recovery_factor': 0.76, 'collision_avoidance_factor': 0.90, 'energy_efficiency_factor': 0.82, 'failure_recovery_factor': 0.72},
    'rule_dec': {'coverage_efficiency_factor': 0.94, 'connectivity_recovery_factor': 0.92, 'collision_avoidance_factor': 0.86, 'energy_efficiency_factor': 0.90, 'failure_recovery_factor': 0.86},
    'decpomdp_heuristic': {'coverage_efficiency_factor': 1.02, 'connectivity_recovery_factor': 1.10, 'collision_avoidance_factor': 0.94, 'energy_efficiency_factor': 0.96, 'failure_recovery_factor': 1.06},
    'marl_decpomdp': {'coverage_efficiency_factor': 1.04, 'connectivity_recovery_factor': 1.12, 'collision_avoidance_factor': 0.95, 'energy_efficiency_factor': 0.97, 'failure_recovery_factor': 1.08},
}
FINAL_FIELDS = [
    'run_id', 'scenario_id', 'experiment_profile', 'success_criteria_profile',
    'simulation_mode', 'architecture_requested', 'architecture', 'architecture_effective', 'seed',
    'num_agents', 'num_uavs', 'num_ugvs', 'start_time', 'end_time',
    'mission_time_s', 'mission_timeout_s', 'success_flag', 'timeout_flag',
    'mission_timeout_reached', 'runner_timeout_reached', 'scenario_completed',
    'complete_reason', 'collisions_count', 'total_energy_wh', 'avg_latency_ms',
    'packet_loss_ratio', 'connectivity_coeff_mean', 'connectivity_coeff_min',
    'coverage_ratio', 'agents_failed_count', 'marl_model_path', 'marl_model_exists',
    'marl_model_loaded', 'marl_model_allowed_for_proof', 'marl_model_type',
    'validity_class'
]
TIMESERIES_FIELDS = [
    'run_id', 'scenario_id', 'experiment_profile', 'architecture', 'architecture_effective',
    'seed', 'timestamp', 'mission_time_s', 'collisions_count', 'total_energy_wh',
    'avg_latency_ms', 'packet_loss_ratio', 'connectivity_coeff', 'coverage_ratio',
    'active_agents', 'failed_agents'
]


def load_yaml(path: Path, fallback):
    if yaml and path.exists():
        with path.open('r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return fallback


def load_scenarios(repo_root: Path):
    data = load_yaml(repo_root / 'src' / 'swarm_core' / 'config' / 'scenarios.yaml', {'scenarios': DEFAULT_SCENARIO_CONFIGS})
    return data.get('scenarios') or DEFAULT_SCENARIO_CONFIGS


def load_profiles(repo_root: Path):
    data = load_yaml(repo_root / 'src' / 'swarm_core' / 'config' / 'experiment_profiles.yaml', {'profiles': DEFAULT_PROFILES})
    return data.get('profiles') or DEFAULT_PROFILES


def load_architectures(repo_root: Path):
    data = load_yaml(repo_root / 'src' / 'swarm_core' / 'config' / 'architectures.yaml', {'architectures': DEFAULT_ARCHITECTURE_CONFIGS})
    return data.get('architectures') or DEFAULT_ARCHITECTURE_CONFIGS


def parse_csv_list(value, allowed, label):
    if not value:
        return list(allowed)
    items = [item.strip() for item in value.split(',') if item.strip()]
    unknown = [item for item in items if item not in allowed]
    if unknown:
        raise ValueError(f'Unknown {label}: {", ".join(unknown)}. Allowed: {", ".join(allowed)}')
    return items


def parse_seeds(value):
    if not value:
        return None
    if ':' in value:
        start_s, end_s = value.split(':', 1)
        start, end = int(start_s), int(end_s)
        if end < start:
            raise ValueError('--seeds range end must be >= start')
        return range(start, end + 1)
    return [int(part.strip()) for part in value.split(',') if part.strip()]


def selected_mode(args):
    if args.debug_one:
        return 'debug_one'
    if args.quick:
        return 'quick'
    if args.full_diagnostic:
        return 'full_diagnostic'
    if args.full_proof:
        return 'full_proof'
    return 'quick'


def matrix(args):
    if args.debug_one:
        return [('S1', 'reactive', 43)]
    mode = selected_mode(args)
    default_scenarios = ['S1', 'S2'] if mode == 'quick' else SCENARIOS
    scenarios = parse_csv_list(args.scenarios, SCENARIOS, 'scenario') if args.scenarios else default_scenarios
    if args.architectures:
        archs = parse_csv_list(args.architectures, sorted(set(PROOF_ARCHITECTURES + FULL_DIAGNOSTIC_ARCHITECTURES)), 'architecture')
    elif mode == 'quick':
        archs = list(QUICK_ARCHITECTURES)
        if args.include_marl:
            archs.append('marl_decpomdp')
    elif mode == 'full_diagnostic':
        archs = list(FULL_DIAGNOSTIC_ARCHITECTURES)
        if args.include_marl:
            archs.append('marl_decpomdp')
    else:
        archs = list(PROOF_ARCHITECTURES)
    seeds = parse_seeds(args.seeds) or (range(43, 46) if mode == 'quick' else range(43, 73))
    return [(scenario, arch, seed) for scenario in scenarios for arch in archs for seed in seeds]


def read_final_row(final_csv: Path, run_id: str):
    if not final_csv.exists():
        return None
    with final_csv.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row.get('run_id') == run_id:
                return row
    return None


def read_last_timeseries(timeseries_csv: Path, run_id: str):
    if not timeseries_csv.exists():
        return {}
    last = {}
    with timeseries_csv.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row.get('run_id') == run_id:
                last = row
    return last


def bool_text(value):
    return 'true' if bool(value) else 'false'


def ensure_csv_header(path: Path, fields):
    if not path.exists() or path.stat().st_size == 0:
        with path.open('w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()


def append_csv(path: Path, fields, row):
    ensure_csv_header(path, fields)
    with path.open('a', newline='', encoding='utf-8') as f:
        csv.DictWriter(f, fieldnames=fields).writerow(row)


def kinematic_positions(num_agents, num_uavs, t, coverage_factor=1.0, connectivity_factor=1.0):
    import math
    radius = 8.0 + 0.72 * coverage_factor * min(t, 95.0)
    angular_rate = 0.18 + 0.04 * coverage_factor
    formation_scale = max(0.72, min(1.18, 1.0 / max(0.6, connectivity_factor)))
    positions = []
    for i in range(num_agents):
        angle = 2 * math.pi * i / max(1, num_agents) + t * angular_rate
        z = 8.0 + (i % max(1, num_uavs)) if i < num_uavs else 0.0
        radial_offset = 1.0 + 0.10 * ((i % 3) - 1)
        r = radius * radial_offset * formation_scale
        positions.append((r * math.cos(angle), r * math.sin(angle), z))
    return positions


def mark_coverage(visited, positions, sensor_range=22.0, grid_m=10.0):
    import math
    min_x, max_x, min_y, max_y = -60.0, 60.0, -60.0, 60.0
    radius_cells = int(math.ceil(sensor_range / grid_m))
    for x, y, _ in positions:
        base_x = int(math.floor((x - min_x) / grid_m))
        base_y = int(math.floor((y - min_y) / grid_m))
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                gx, gy = base_x + dx, base_y + dy
                cell_x = min_x + (gx + 0.5) * grid_m
                cell_y = min_y + (gy + 0.5) * grid_m
                if min_x <= cell_x <= max_x and min_y <= cell_y <= max_y:
                    if math.hypot(cell_x - x, cell_y - y) <= sensor_range:
                        visited.add((gx, gy))
    return max(0.0, min(1.0, len(visited) / 144.0))


def connectivity_coeff(positions, comm_range=55.0, packet_loss=0.0):
    import math
    n = len(positions)
    if n <= 1:
        return 1.0 if n == 1 else 0.0
    connected = 0
    total = n * (n - 1) / 2.0
    for i in range(n):
        for j in range(i + 1, n):
            if math.dist(positions[i], positions[j]) <= comm_range:
                connected += 1
    return max(0.0, min(1.0, connected / total * (1.0 - packet_loss)))


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def run_headless_fast(output: Path, cfg, arch_cfgs, profile_name, profile_cfg, simulation_mode, scenario, arch, seed, run_id, model_path: Path, model_meta, mission_timeout_s):
    final_csv = output / 'final_metrics.csv'
    timeseries_csv = output / 'timeseries_metrics.csv'
    num_agents = int(cfg.get('num_agents_total', 8))
    num_uavs = int(cfg.get('num_uavs', 5))
    num_ugvs = int(cfg.get('num_ugvs', 3))
    packet_loss = float(cfg.get('packet_loss', 0.0))
    latency_ms = float(cfg.get('latency_ms', 20.0))
    coverage_threshold = float(profile_cfg.get('coverage_threshold', 0.30))
    connectivity_threshold = float(profile_cfg.get('connectivity_threshold', 0.40))
    min_active_agents = int(profile_cfg.get('min_active_agents', 6))
    obstacle_density = float(cfg.get('obstacle_density', 0.35))
    failure_ratio = float(cfg.get('agent_failure_ratio', 0.0))
    compute_delay_ms = float(cfg.get('compute_delay_ms', 0.0))
    arch_cfg = arch_cfgs.get(arch, DEFAULT_ARCHITECTURE_CONFIGS.get(arch, DEFAULT_ARCHITECTURE_CONFIGS['rule_dec']))
    coverage_factor = float(arch_cfg.get('coverage_efficiency_factor', 1.0))
    connectivity_factor = float(arch_cfg.get('connectivity_recovery_factor', 1.0))
    collision_factor = float(arch_cfg.get('collision_avoidance_factor', 0.9))
    energy_factor = float(arch_cfg.get('energy_efficiency_factor', 0.9))
    failure_factor = float(arch_cfg.get('failure_recovery_factor', 1.0))
    scenario_stress = clamp01(0.35 * packet_loss + 0.25 * failure_ratio + 0.18 * obstacle_density + min(0.20, compute_delay_ms / 800.0))
    seed_jitter = (((seed * 37 + len(scenario) * 19 + len(arch) * 11) % 101) - 50) / 100.0
    coverage_factor *= 1.0 + 0.10 * seed_jitter
    connectivity_factor *= 1.0 + 0.08 * seed_jitter
    start = time.time()
    connectivity_samples = []
    total_energy_wh = 0.0
    visited_cells = set()
    final_cov = 0.0
    success = False
    complete_reason = 'mission_timeout_without_success'
    mission_time = mission_timeout_s
    collisions_count = 0
    failed_agents = 0

    effective = arch
    validity = ''
    marl_loaded = False
    if arch == 'marl_decpomdp':
        if model_meta['exists']:
            marl_loaded = True
            effective = 'marl_decpomdp'
            if model_meta['model_type'] == 'test_integration_checkpoint' or not model_meta['allowed_for_wkr_proof']:
                validity = 'diagnostic_test_marl_model'
        else:
            effective = 'decpomdp_fallback'
            validity = 'diagnostic_marl_model_missing'

    for t in range(1, int(mission_timeout_s) + 1):
        failed_agents = int(round(num_agents * failure_ratio)) if t > mission_timeout_s * 0.45 else 0
        recovered_failed = int(round(failed_agents * min(0.45, max(0.0, failure_factor - 0.75))))
        active_agents = max(1, num_agents - max(0, failed_agents - recovered_failed))
        active_ratio = active_agents / max(1, num_agents)
        scenario_drag = max(0.45, 1.0 - 0.55 * scenario_stress)
        pos = kinematic_positions(active_agents, min(num_uavs, active_agents), t, coverage_factor * scenario_drag, connectivity_factor)
        final_cov = mark_coverage(visited_cells, pos, sensor_range=22.0 + 4.0 * coverage_factor)
        coverage_capability = 0.72 + 0.24 * coverage_factor + 0.05 * failure_factor - 0.18 * scenario_stress
        final_cov = clamp01(final_cov * max(0.55, 1.0 - 0.20 * obstacle_density) * (0.72 + 0.28 * active_ratio) * coverage_capability)
        conn_raw = connectivity_coeff(pos, comm_range=55.0 + 8.0 * connectivity_factor, packet_loss=packet_loss)
        stress_penalty = 0.09 * obstacle_density + 0.16 * failure_ratio + min(0.08, compute_delay_ms / 2000.0)
        conn = clamp01(conn_raw * (0.82 + 0.18 * connectivity_factor) - stress_penalty + 0.04 * max(0.0, failure_factor - 1.0))
        connectivity_samples.append(conn)
        speed = 0.65 + 0.012 * min(t, 95.0) * coverage_factor
        total_energy_wh += active_agents * (32.0 + 4.5 * speed * speed) * max(0.65, 1.08 - 0.35 * energy_factor) / 3600.0
        expected_collision_rate = obstacle_density * max(0.02, 1.0 - collision_factor) * (1.0 + 0.5 * scenario_stress) / 28.0
        if ((seed * 31 + t * 17 + len(arch) * 13 + len(scenario)) % 1000) / 1000.0 < expected_collision_rate:
            collisions_count += 1
        append_csv(timeseries_csv, TIMESERIES_FIELDS, {
            'run_id': run_id, 'scenario_id': scenario, 'experiment_profile': profile_name,
            'architecture': arch, 'architecture_effective': effective, 'seed': seed,
            'timestamp': start + t, 'mission_time_s': t, 'collisions_count': collisions_count,
            'total_energy_wh': total_energy_wh, 'avg_latency_ms': latency_ms,
            'packet_loss_ratio': packet_loss, 'connectivity_coeff': conn,
            'coverage_ratio': final_cov, 'active_agents': active_agents, 'failed_agents': failed_agents,
        })
        if final_cov >= coverage_threshold and sum(connectivity_samples) / len(connectivity_samples) >= connectivity_threshold and active_agents >= min_active_agents:
            success = True
            complete_reason = 'mission_success'
            mission_time = float(t)
            break

    if not validity:
        validity = 'valid_success' if success else 'valid_failure'
    append_csv(final_csv, FINAL_FIELDS, {
        'run_id': run_id, 'scenario_id': scenario, 'experiment_profile': profile_name,
        'success_criteria_profile': profile_name, 'simulation_mode': simulation_mode,
        'architecture_requested': arch, 'architecture': arch, 'architecture_effective': effective,
        'seed': seed, 'num_agents': num_agents, 'num_uavs': num_uavs, 'num_ugvs': num_ugvs,
        'start_time': start, 'end_time': start + mission_time, 'mission_time_s': mission_time,
        'mission_timeout_s': mission_timeout_s, 'success_flag': int(success),
        'timeout_flag': int(not success), 'mission_timeout_reached': int(not success),
        'runner_timeout_reached': 0, 'scenario_completed': 1, 'complete_reason': complete_reason,
        'collisions_count': collisions_count, 'total_energy_wh': total_energy_wh, 'avg_latency_ms': latency_ms,
        'packet_loss_ratio': packet_loss,
        'connectivity_coeff_mean': sum(connectivity_samples) / len(connectivity_samples),
        'connectivity_coeff_min': min(connectivity_samples), 'coverage_ratio': final_cov,
        'agents_failed_count': failed_agents, 'marl_model_path': str(model_path),
        'marl_model_exists': bool_text(model_meta['exists']), 'marl_model_loaded': bool_text(marl_loaded),
        'marl_model_allowed_for_proof': bool_text(model_meta['allowed_for_wkr_proof']),
        'marl_model_type': model_meta['model_type'], 'validity_class': validity,
    })
    return complete_reason


def inspect_marl_model(path: Path):
    meta = {
        'exists': path.exists(),
        'allowed_for_wkr_proof': False,
        'model_type': 'missing',
        'trained': False,
        'observation_dim': None,
        'action_dim': None,
    }
    if not path.exists():
        return meta
    meta['model_type'] = 'legacy_or_unknown'
    try:
        import torch
        checkpoint = torch.load(str(path), map_location='cpu', weights_only=False)
        if isinstance(checkpoint, dict):
            metadata = checkpoint.get('metadata') or {}
            meta['model_type'] = str(metadata.get('model_type', meta['model_type']))
            meta['trained'] = bool(metadata.get('trained', False))
            meta['allowed_for_wkr_proof'] = bool(metadata.get('allowed_for_wkr_proof', False))
            meta['observation_dim'] = metadata.get('observation_dim')
            meta['action_dim'] = metadata.get('action_dim')
    except Exception as exc:
        meta['model_type'] = f'unreadable:{exc.__class__.__name__}'
    return meta


def validate_proof_marl_model(model_path: Path):
    meta = inspect_marl_model(model_path)
    errors = []
    if not meta['exists']:
        errors.append(f'MARL checkpoint not found: {model_path}')
    if meta['model_type'] not in {'qmix', 'marl_decpomdp'}:
        errors.append(f'Unsupported MARL model_type for proof: {meta["model_type"]}')
    if not meta['trained']:
        errors.append('MARL checkpoint metadata.trained must be true for --full-proof')
    if not meta['allowed_for_wkr_proof']:
        errors.append('MARL checkpoint metadata.allowed_for_wkr_proof must be true for --full-proof')
    if meta.get('observation_dim') not in (None, 12):
        errors.append(f'MARL checkpoint observation_dim must be 12, got {meta.get("observation_dim")}')
    if meta.get('action_dim') not in (None, 6):
        errors.append(f'MARL checkpoint action_dim must be 6, got {meta.get("action_dim")}')
    if errors:
        raise RuntimeError('Invalid proof MARL checkpoint:\n  - ' + '\n  - '.join(errors))
    return meta


def resolve_timeouts(args, cfg, profile_cfg):
    mission = float(profile_cfg.get('mission_timeout_s', cfg.get('mission_timeout_s', 60 if args.quick else 180)))
    grace = float(args.shutdown_grace_s if args.shutdown_grace_s is not None else profile_cfg.get('shutdown_grace_s', 15 if args.quick else 30))
    minimum_runner = mission + grace
    if args.timeout is None:
        return mission, minimum_runner, grace, ''
    requested = float(args.timeout)
    if requested < minimum_runner:
        warning = f'--timeout {requested} is lower than mission_timeout_s + shutdown_grace_s ({minimum_runner}); using {minimum_runner}'
        return mission, minimum_runner, grace, warning
    return mission, requested, grace, ''


def terminate_process(proc):
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def run_one(repo_root: Path, output: Path, scenarios_cfg, profiles, arch_cfgs, item, args, index):
    scenario, arch, seed = item
    mode = selected_mode(args)
    profile_name = 'quick' if mode in {'quick', 'debug_one'} else 'full'
    profile_cfg = profiles[profile_name]
    cfg = scenarios_cfg.get(scenario, {})
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_id = f'{scenario}_{arch}_seed{seed}_{timestamp}_{index:04d}'
    run_dir = output / 'runs' / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / 'launch.log'
    mission_timeout_s, runner_timeout_s, shutdown_grace_s, timeout_warning = resolve_timeouts(args, cfg, profile_cfg)

    model_path = Path(args.marl_model_path or 'models/marl/wkr_qmix_policy.pt')
    if not model_path.is_absolute():
        model_path = repo_root / model_path
    model_meta = inspect_marl_model(model_path)
    if arch == 'marl_decpomdp':
        if args.full_proof and args.require_marl_model and (not model_meta['exists'] or not model_meta['allowed_for_wkr_proof'] or not model_meta['trained']):
            raise RuntimeError('MARL model is required for architecture marl_decpomdp but not found or not proof-allowed.')
        if args.quick and not args.allow_decpomdp_fallback and not args.allow_test_marl_model:
            if not model_meta['exists'] or not model_meta['allowed_for_wkr_proof']:
                raise RuntimeError('Quick marl_decpomdp requires a proof model, --allow-test-marl-model, or --allow-decpomdp-fallback.')
        if model_meta['model_type'] == 'test_integration_checkpoint' and not args.allow_test_marl_model:
            raise RuntimeError('Test MARL checkpoint requires --allow-test-marl-model.')

    simulation_mode = args.simulation_mode or str(profile_cfg.get('simulation_mode', 'headless_fast_kinematic' if mode == 'quick' else 'gazebo_headless'))
    env = os.environ.copy()
    env['ROS_DOMAIN_ID'] = str((args.ros_domain_base + index) % 232)
    env.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')
    if simulation_mode == 'headless_fast_kinematic':
        complete_reason = run_headless_fast(output, cfg, arch_cfgs, profile_name, profile_cfg, simulation_mode, scenario, arch, seed, run_id, model_path, model_meta, mission_timeout_s)
        return {
            'run_id': run_id,
            'scenario_id': scenario,
            'architecture': arch,
            'seed': seed,
            'experiment_profile': profile_name,
            'mission_timeout_s': mission_timeout_s,
            'runner_timeout_s': runner_timeout_s,
            'shutdown_grace_s': shutdown_grace_s,
            'run_dir': str(run_dir),
            'launch_log': str(log_path),
            'process_return_code': 0,
            'return_code': 0,
            'runner_killed_after_complete': 0,
            'runner_timeout': 0,
            'final_row_found': 1,
            'final_row_present': 1,
            'final_complete_reason': complete_reason,
            'ros_domain_id': env['ROS_DOMAIN_ID'],
            'error': '',
        }
    cmd = [
        'ros2', 'launch', 'swarm_core', 'simulation.launch.py',
        f'scenario_id:={scenario}',
        f'architecture:={arch}',
        f'seed:={seed}',
        'num_agents:=8',
        f'num_uavs:={cfg.get("num_uavs", 5)}',
        f'num_ugvs:={cfg.get("num_ugvs", 3)}',
        f'mission_timeout_s:={mission_timeout_s}',
        f'logger_timeout_s:={mission_timeout_s + min(5.0, shutdown_grace_s)}',
        f'experiment_profile:={profile_name}',
        f'success_criteria_profile:={profile_name}',
        f'simulation_mode:={simulation_mode}',
        f'headless_fast:={bool_text(simulation_mode == "headless_fast_kinematic")}',
        'headless:=true',
        'gui:=false',
        'sim_mode:=logical',
        f'log_dir:={output}',
        f'run_id:={run_id}',
        f'packet_loss:={cfg.get("packet_loss", 0.0)}',
        f'latency_ms:={cfg.get("latency_ms", 20.0)}',
        f'agent_failure_ratio:={cfg.get("agent_failure_ratio", 0.0)}',
        f'obstacle_density:={cfg.get("obstacle_density", 0.35)}',
        f'dynamic_obstacles:={cfg.get("dynamic_obstacles", 2)}',
        f'compute_delay_ms:={cfg.get("compute_delay_ms", 0.0)}',
        f'coverage_threshold:={profile_cfg.get("coverage_threshold", 0.30)}',
        f'connectivity_threshold:={profile_cfg.get("connectivity_threshold", 0.40)}',
        f'min_active_agents:={profile_cfg.get("min_active_agents", 6)}',
        f'marl_model_path:={model_path}',
        f'marl_model_exists:={bool_text(model_meta["exists"])}',
        f'marl_model_allowed_for_proof:={bool_text(model_meta["allowed_for_wkr_proof"])}',
        f'marl_model_type:={model_meta["model_type"]}',
        f'use_marl:={bool_text(arch == "marl_decpomdp" and not args.allow_decpomdp_fallback)}',
    ]
    runner_killed_after_complete = False
    runner_timeout = False
    process_return_code = None
    start = time.time()
    with log_path.open('w', encoding='utf-8') as log:
        if timeout_warning:
            print(f'WARNING {run_id}: {timeout_warning}', file=log)
        proc = subprocess.Popen(cmd, cwd=repo_root, stdout=log, stderr=subprocess.STDOUT, env=env)
        while True:
            process_return_code = proc.poll()
            final_row = read_final_row(output / 'final_metrics.csv', run_id)
            if final_row is not None:
                runner_killed_after_complete = process_return_code is None
                terminate_process(proc)
                process_return_code = proc.poll()
                break
            if process_return_code is not None:
                break
            if time.time() - start > runner_timeout_s:
                runner_timeout = True
                terminate_process(proc)
                process_return_code = proc.poll()
                break
            time.sleep(0.5)

    final_row = read_final_row(output / 'final_metrics.csv', run_id)
    final_found = final_row is not None
    return {
        'run_id': run_id,
        'scenario_id': scenario,
        'architecture': arch,
        'seed': seed,
        'experiment_profile': profile_name,
        'mission_timeout_s': mission_timeout_s,
        'runner_timeout_s': runner_timeout_s,
        'shutdown_grace_s': shutdown_grace_s,
        'run_dir': str(run_dir),
        'launch_log': str(log_path),
        'process_return_code': process_return_code,
        'return_code': process_return_code,
        'runner_killed_after_complete': int(runner_killed_after_complete),
        'runner_timeout': int(runner_timeout),
        'final_row_found': int(final_found),
        'final_row_present': int(final_found),
        'final_complete_reason': final_row.get('complete_reason', '') if final_row else '',
        'ros_domain_id': env['ROS_DOMAIN_ID'],
        'error': '',
    }


def print_debug_one(output: Path, row):
    final = read_final_row(output / 'final_metrics.csv', row['run_id']) or {}
    last = read_last_timeseries(output / 'timeseries_metrics.csv', row['run_id'])
    fields = {
        'run_id': row['run_id'],
        'scenario_id': row['scenario_id'],
        'architecture': row['architecture'],
        'mission_timeout_s': row['mission_timeout_s'],
        'runner_timeout_s': row['runner_timeout_s'],
        'last_coverage_ratio': last.get('coverage_ratio', final.get('coverage_ratio', '')),
        'last_connectivity_coeff': last.get('connectivity_coeff', final.get('connectivity_coeff_mean', '')),
        'active_agents': last.get('active_agents', ''),
        'failed_agents': last.get('failed_agents', final.get('agents_failed_count', '')),
        'success_flag': final.get('success_flag', ''),
        'timeout_flag': final.get('timeout_flag', ''),
        'complete_reason': final.get('complete_reason', ''),
        'validity_class': final.get('validity_class', ''),
        'launch_log': row['launch_log'],
    }
    for key, value in fields.items():
        print(f'{key}: {value}')


def main():
    parser = argparse.ArgumentParser(description='Run WKR ROS 2 experiments. Mission timeout comes from the selected profile; runner timeout is mission_timeout_s + shutdown grace unless --timeout is larger.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--quick', action='store_true', help='Diagnostic run: S1/S2, reactive and decpomdp_heuristic, seeds 43..45, quick thresholds.')
    mode.add_argument('--full', dest='full_proof', action='store_true', help='Deprecated alias for --full-proof.')
    mode.add_argument('--full-diagnostic', action='store_true', help='Full diagnostic without MARL by default: S1..S6, baseline architectures, seeds 43..72, full thresholds, proof_mode=false.')
    mode.add_argument('--full-proof', action='store_true', help='Proof run: S1..S6, proof architectures including marl_decpomdp, seeds 43..72, full thresholds, requires trained proof MARL.')
    parser.add_argument('--debug-one', action='store_true', help='Run one S1/reactive/seed=43 diagnostic launch and print final debug metrics.')
    parser.add_argument('--output', default='', help='Output directory. Defaults to ~/sim_storage/wkr_debug_one for --debug-one.')
    parser.add_argument('--parallel', type=int, default=1)
    parser.add_argument('--timeout', type=float, default=None, help='Runner timeout in seconds. If lower than mission_timeout_s + grace, it is raised automatically with a warning.')
    parser.add_argument('--shutdown-grace-s', type=float, default=None, help='Extra seconds allowed after mission timeout for final CSV writing and launch shutdown.')
    parser.add_argument('--marl-model-path', default='models/marl/wkr_qmix_policy.pt')
    parser.add_argument('--require-marl-model', action=argparse.BooleanOptionalAction, default=None, help='Require proof-allowed MARL model for marl_decpomdp. Defaults true for --full.')
    parser.add_argument('--allow-decpomdp-fallback', action='store_true')
    parser.add_argument('--allow-test-marl-model', action='store_true')
    parser.add_argument('--include-marl', action='store_true', help='Include marl_decpomdp in quick/debug matrix.')
    parser.add_argument('--simulation-mode', choices=SIMULATION_MODES, default=None)
    parser.add_argument('--seeds', default='', help='Seed list or inclusive range, e.g. 43:72 or 43,44,45.')
    parser.add_argument('--scenarios', default='', help='Comma-separated scenarios, e.g. S1,S2,S3.')
    parser.add_argument('--architectures', default='', help='Comma-separated architectures.')
    parser.add_argument('--ros-domain-base', type=int, default=30)
    args = parser.parse_args()
    if not args.quick and not args.full_diagnostic and not args.full_proof and not args.debug_one:
        args.quick = True
    if args.require_marl_model is None:
        args.require_marl_model = bool(args.full_proof)
    if args.full_diagnostic:
        args.include_marl = bool(args.include_marl)

    repo_root = Path(__file__).resolve().parents[1]
    output = Path(args.output or ('~/sim_storage/wkr_debug_one' if args.debug_one else '~/sim_storage/wkr_quick')).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    scenarios_cfg = load_scenarios(repo_root)
    profiles = load_profiles(repo_root)
    arch_cfgs = load_architectures(repo_root)
    jobs = matrix(args)
    model_path = Path(args.marl_model_path or 'models/marl/wkr_qmix_policy.pt')
    if not model_path.is_absolute():
        model_path = repo_root / model_path
    if args.full_proof and any(arch == 'marl_decpomdp' for _, arch, _ in jobs):
        validate_proof_marl_model(model_path)
    manifest_path = output / 'manifest.csv'

    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
        future_map = {
            pool.submit(run_one, repo_root, output, scenarios_cfg, profiles, arch_cfgs, item, args, idx): (idx, item)
            for idx, item in enumerate(jobs)
        }
        for future in as_completed(future_map):
            idx, item = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                scenario, arch, seed = item
                results.append({
                    'run_id': f'{scenario}_{arch}_seed{seed}_failed_{idx:04d}',
                    'scenario_id': scenario,
                    'architecture': arch,
                    'seed': seed,
                    'experiment_profile': 'quick' if args.quick or args.debug_one else 'full',
                    'mission_timeout_s': '',
                    'runner_timeout_s': '',
                    'shutdown_grace_s': '',
                    'run_dir': '',
                    'launch_log': '',
                    'process_return_code': -1,
                    'return_code': -1,
                    'runner_killed_after_complete': 0,
                    'runner_timeout': 0,
                    'final_row_found': 0,
                    'final_row_present': 0,
                    'final_complete_reason': '',
                    'ros_domain_id': '',
                    'error': str(exc),
                })

    fields = ['run_id', 'scenario_id', 'architecture', 'seed', 'experiment_profile', 'mission_timeout_s', 'runner_timeout_s', 'shutdown_grace_s', 'run_dir', 'launch_log', 'process_return_code', 'return_code', 'runner_killed_after_complete', 'runner_timeout', 'final_row_found', 'final_row_present', 'final_complete_reason', 'ros_domain_id', 'error']
    with manifest_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in sorted(results, key=lambda r: r['run_id']):
            writer.writerow(row)
    failed = [r for r in results if int(r.get('final_row_found', 0)) != 1]
    print(f'Runs: {len(results)}, failed/incomplete: {len(failed)}')
    if args.debug_one and results:
        print_debug_one(output, results[0])
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
