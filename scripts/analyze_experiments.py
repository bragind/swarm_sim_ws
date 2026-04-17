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
        
        # Поиск метрик в логе (регулярные выражения под ваш формат вывода)
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
    
    for log_file in log_path.glob('*.log'):
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