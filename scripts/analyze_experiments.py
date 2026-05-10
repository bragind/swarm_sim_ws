#!/usr/bin/env python3
"""
Автоматический парсер логов экспериментов.
Генерирует сводную таблицу для статистического анализа и графиков.
"""
import os
import re
import csv
import json
from pathlib import Path
from datetime import datetime

def _apply_json_metrics(metrics: dict, json_data: dict) -> None:
    """Заполняет метрики из JSON experiment_logger."""
    key_map = {
        'run_id': 'run_id',
        'scenario_id': 'scenario_id',
        'seed': 'seed',
        'mission_time_s': 'mission_time_s',
        'success_flag': 'success_flag',
        'collisions_count': 'collisions_count',
        'total_energy_wh': 'total_energy_wh',
        'avg_latency_ms': 'avg_latency_ms',
        'packet_loss_ratio': 'packet_loss_ratio',
        'connectivity_coeff': 'connectivity_coeff',
        'num_agents': 'num_agents',
    }
    for dst, src in key_map.items():
        if src in json_data and json_data[src] is not None:
            metrics[dst] = json_data[src]

def _apply_csv_metrics(metrics: dict, csv_path: Path) -> bool:
    """
    Заполняет метрики из CSV experiment_logger.
    Берём последнюю строку как финальный срез метрик.
    """
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore', newline='') as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return False
        row = rows[-1]

        def to_num(value):
            if value is None or value == '':
                return None
            try:
                return float(value) if '.' in str(value) else int(value)
            except ValueError:
                return None

        if row.get('run_id'):
            metrics['run_id'] = row['run_id']
        if row.get('scenario_id'):
            metrics['scenario_id'] = row['scenario_id']
        if row.get('seed'):
            parsed_seed = to_num(row.get('seed'))
            if parsed_seed is not None:
                metrics['seed'] = int(parsed_seed)

        for key in [
            'mission_time_s', 'collisions_count', 'total_energy_wh',
            'avg_latency_ms', 'packet_loss_ratio', 'connectivity_coeff', 'num_agents'
        ]:
            parsed = to_num(row.get(key))
            if parsed is not None:
                metrics[key] = parsed

        success_val = row.get('success_flag')
        parsed_success = to_num(success_val)
        if parsed_success is not None:
            metrics['success_flag'] = 1 if int(parsed_success) != 0 else 0
        return True
    except Exception:
        return False

def _load_structured_metrics(log_path: Path, metrics: dict) -> bool:
    """
    Пробует загрузить метрики из JSON/CSV experiment_logger для сценария+seed.
    Ищем в той же директории: <scenario>_*_<seed>.json/.csv.
    """
    scenario = metrics.get('scenario_id')
    seed = metrics.get('seed')
    if not scenario or seed is None:
        return False

    parent = log_path.parent
    json_candidates = sorted(
        parent.glob(f"{scenario}_*_{seed}.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    for json_file in json_candidates:
        try:
            with open(json_file, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            if isinstance(data, dict):
                _apply_json_metrics(metrics, data)
                return True
        except Exception:
            continue

    csv_candidates = sorted(
        parent.glob(f"{scenario}_*_{seed}.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    for csv_file in csv_candidates:
        if _apply_csv_metrics(metrics, csv_file):
            return True

    return False

def parse_log_file(log_path: str) -> dict:
    """Извлекает метрики из одного лог-файла"""
    metrics = {
        'run_id': Path(log_path).stem,
        'scenario_id': None,
        'seed': None,
        'mission_time_s': None,
        'success_flag': 0,
        'collisions_count': 0,
        'total_energy_wh': None,
        'avg_latency_ms': None,
        'packet_loss_ratio': None,
        'connectivity_coeff': None,
        'num_agents': None,
        'error': None
    }
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Извлечение базовой информации из имени файла
        # Формат: S1_run1_seed43
        match = re.match(r'(\w+)_run(\d+)_seed(\d+)', Path(log_path).stem)
        if match:
            metrics['scenario_id'] = match.group(1)
            metrics['seed'] = int(match.group(3))
        
        # 1) Приоритет: structured-метрики от experiment_logger (.json/.csv)
        structured_loaded = _load_structured_metrics(Path(log_path), metrics)

        # 2) Fallback: старый regex-парсинг текстовых launch-логов
        if not structured_loaded:
            patterns = {
                'mission_time_s': r'mission_time[:\s]+([\d.]+)\s*s',
                'success_flag': r'success[:\s]+(true|false|1|0)',
                'collisions_count': r'collisions[:\s]+(\d+)',
                'total_energy_wh': r'energy[:\s]+([\d.]+)\s*Wh',
                'avg_latency_ms': r'latency[:\s]+([\d.]+)\s*ms',
                'packet_loss_ratio': r'packet_loss[:\s]+([\d.]+)',
                'connectivity_coeff': r'connectivity[:\s]+([\d.]+)',
                'num_agents': r'agents[:\s]+(\d+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    val = match.group(1).lower()
                    if key == 'success_flag':
                        metrics[key] = 1 if val in ['true', '1'] else 0
                    else:
                        try:
                            metrics[key] = float(val) if '.' in val else int(val)
                        except ValueError:
                            pass
        
        # Проверка на ошибки в логе
        if 'ERROR' in content or 'FATAL' in content or 'Traceback' in content:
            metrics['error'] = 'runtime_error'
        elif 'timeout' in content.lower():
            metrics['error'] = 'timeout'
            
    except Exception as e:
        metrics['error'] = f'parse_error: {str(e)}'
    
    return metrics

def aggregate_results(log_dir: str, output_csv: str):
    """Агрегирует все логи в единый CSV"""
    log_path = Path(log_dir)
    results = []
    
    log_files = sorted(log_path.glob('*.log'))
    run_log_re = re.compile(r'^\w+_run\d+_seed\d+\.log$')
    for log_file in log_files:
        if not run_log_re.match(log_file.name):
            continue
        metrics = parse_log_file(str(log_file))
        results.append(metrics)
        print(f"📄 Обработан: {log_file.name} → {metrics['success_flag'] and '✅' or '❌'}")
    
    # Сортировка по сценарию и сид
    results.sort(key=lambda x: (x['scenario_id'] or '', x['seed'] or 0))
    
    # Запись в CSV
    if results:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\n✅ Сводная таблица сохранена: {output_csv}")
        print(f"📊 Всего прогонов: {len(results)}")
        
        # Краткая статистика
        scenarios = set(r['scenario_id'] for r in results if r['scenario_id'])
        for sc in sorted(scenarios):
            sc_runs = [r for r in results if r['scenario_id'] == sc]
            success = sum(1 for r in sc_runs if r['success_flag'])
            print(f"   {sc}: {len(sc_runs)} прогонов, {success} успешных ({100*success/len(sc_runs):.1f}%)")
    else:
        print("⚠️  Не найдено логов для анализа")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--log_dir', default='/home/swarm/sim_storage/experiments')
    parser.add_argument('--output', default='/home/swarm/sim_storage/exp_results.csv')
    args = parser.parse_args()
    
    aggregate_results(args.log_dir, args.output)