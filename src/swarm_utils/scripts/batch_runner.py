#!/usr/bin/env python3
"""
Python-based batch runner. Handles parallel execution, logging, and CSV aggregation.
"""
import subprocess
import os
import time
import csv
import concurrent.futures
from datetime import datetime

class BatchRunner:
    def __init__(self, config):
        self.config = config
        self.log_dir = config.get('log_dir', '/tmp/swarm_logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.results_file = os.path.join(self.log_dir, 'batch_results.csv')
        
    def run_single(self, scenario, seed):
        cmd = [
            'ros2', 'launch', 'swarm_core', 'simulation.launch.py',
            f'scenario_id:={scenario}',
            f'seed:={seed}',
            'num_uavs:=5', 'num_ugvs:=3', 'use_marl:=true'
        ]
        log_file = os.path.join(self.log_dir, f'{scenario}_{seed}.log')
        
        try:
            with open(log_file, 'w') as f:
                proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, 
                                      timeout=self.config.get('timeout_seconds', 600))
            return {'scenario': scenario, 'seed': seed, 'status': proc.returncode}
        except subprocess.TimeoutExpired:
            return {'scenario': scenario, 'seed': seed, 'status': -1, 'error': 'timeout'}
            
    def run_batch(self):
        scenarios = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']
        runs = self.config.get('runs_per_scenario', 100)
        max_workers = self.config.get('max_parallel', 4)
        
        tasks = []
        for sc in scenarios:
            for r in range(runs):
                tasks.append((sc, 42 + r))
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.run_single, sc, seed): (sc, seed) for sc, seed in tasks}
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                self._save_result(res)
                
    def _save_result(self, res):
        with open(self.results_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=res.keys())
            if f.tell() == 0: writer.writeheader()
            writer.writerow(res)

if __name__ == '__main__':
    runner = BatchRunner({
        'log_dir': os.path.expanduser('~/sim_storage/experiments'),
        'runs_per_scenario': 10,  # Reduced for testing
        'max_parallel': 2,
        'timeout_seconds': 120
    })
    runner.run_batch()