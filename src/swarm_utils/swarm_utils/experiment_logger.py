#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from swarm_msgs.msg import SwarmState
from std_msgs.msg import Float64, Bool
import csv
import json
import os
import time
from datetime import datetime

class ExperimentLogger(Node):
    def __init__(self):
        super().__init__('experiment_logger')
        
        # Параметры
        self.declare_parameter('log_path', os.path.expanduser('~/sim_storage/experiments'))
        self.declare_parameter('scenario_id', 'S1')
        self.declare_parameter('seed', 42)
        self.declare_parameter('csv_output', True)
        self.declare_parameter('timeout', 120.0)  # seconds
        
        self.log_path = self.get_parameter('log_path').value
        self.scenario_id = self.get_parameter('scenario_id').value
        self.seed = self.get_parameter('seed').value
        self.csv_output = self.get_parameter('csv_output').value
        self.timeout_duration = self.get_parameter('timeout').value
        
        os.makedirs(self.log_path, exist_ok=True)
        
        # Переменные состояния эксперимента
        self.start_time = None
        self.end_time = None
        self.mission_time = 0.0
        self.success_flag = False
        self.collisions_count = 0
        self.total_energy_wh = 0.0
        self.avg_latency_ms = 0.0
        self.packet_loss_ratio = 0.0
        self.connectivity_coeff = 1.0
        self.num_agents = 0
        self.last_state_time = None
        
        # Подписки
        self.state_sub = self.create_subscription(SwarmState, '/swarm/state', self.state_callback, 10)
        # НОВЫЕ ПОДПИСКИ
        self.collision_sub = self.create_subscription(Float64, '/swarm/collisions', self.collision_callback, 10)
        self.energy_sub = self.create_subscription(Float64, '/swarm/total_energy', self.energy_callback, 10)
        self.success_sub = self.create_subscription(Bool, '/swarm/success', self.success_callback, 10)
        # Для латентности и потерь пакетов уже есть communication_emulator, который публикует в отдельные топики?
        # Предположим, что они публикуются в /swarm/latency и /swarm/packet_loss, но если нет, оставим нули.
        # Добавим подписки, если эмулятор их публикует.
        self.latency_sub = self.create_subscription(Float64, '/swarm/avg_latency', self.latency_callback, 10)
        self.loss_sub = self.create_subscription(Float64, '/swarm/packet_loss', self.loss_callback, 10)
        
        # Таймер для проверки таймаута
        self.timer = self.create_timer(1.0, self.check_timeout)
        
        self.get_logger().info(f'Experiment logger initialized. Logging to: {self._get_log_filename()}')
    
    def _get_log_filename(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(self.log_path, f'{self.scenario_id}_{timestamp}_{self.seed}')
    
    def state_callback(self, msg: SwarmState):
        if self.start_time is None:
            self.start_time = time.time()
        self.last_state_time = time.time()
        self.num_agents = len(msg.agents)
        self.connectivity_coeff = msg.connectivity_coefficient
        
        # Запись в CSV при каждом обновлении (если включено)
        if self.csv_output:
            self._write_csv_row()
    
    def collision_callback(self, msg: Float64):
        self.collisions_count = int(msg.data)
    
    def energy_callback(self, msg: Float64):
        self.total_energy_wh = msg.data
    
    def success_callback(self, msg: Bool):
        self.success_flag = msg.data
    
    def latency_callback(self, msg: Float64):
        self.avg_latency_ms = msg.data
    
    def loss_callback(self, msg: Float64):
        self.packet_loss_ratio = msg.data
    
    def check_timeout(self):
        if self.start_time is not None and self.last_state_time is not None:
            elapsed = time.time() - self.last_state_time
            if elapsed > self.timeout_duration:
                self.get_logger().warn('Timeout reached, finalizing experiment...')
                self.finalize()
                rclpy.shutdown()
    
    def finalize(self):
        self.end_time = time.time()
        if self.start_time:
            self.mission_time = self.end_time - self.start_time
        
        # Запись финального JSON
        self._write_json()
        self.get_logger().info(f'Experiment completed. Results saved to {self._get_log_filename()}.csv/json')
        self.get_logger().info(f'Mission time: {self.mission_time:.2f}s, Success: {self.success_flag}, Collisions: {self.collisions_count}')
    
    def _write_csv_row(self):
        csv_file = self._get_log_filename() + '.csv'
        file_exists = os.path.isfile(csv_file)
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'run_id', 'scenario_id', 'seed', 'start_time', 'end_time',
                    'mission_time_s', 'success_flag', 'collisions_count',
                    'total_energy_wh', 'avg_latency_ms', 'packet_loss_ratio',
                    'connectivity_coeff', 'num_agents'
                ])
            run_id = f'{self.scenario_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{self.seed}'
            writer.writerow([
                run_id,
                self.scenario_id,
                self.seed,
                self.start_time if self.start_time else '',
                self.end_time if self.end_time else '',
                self.mission_time,
                int(self.success_flag),
                self.collisions_count,
                self.total_energy_wh,
                self.avg_latency_ms,
                self.packet_loss_ratio,
                self.connectivity_coeff,
                self.num_agents
            ])
    
    def _write_json(self):
        json_file = self._get_log_filename() + '.json'
        data = {
            'run_id': f'{self.scenario_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{self.seed}',
            'scenario_id': self.scenario_id,
            'seed': self.seed,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'mission_time_s': self.mission_time,
            'success_flag': int(self.success_flag),
            'collisions_count': self.collisions_count,
            'total_energy_wh': self.total_energy_wh,
            'avg_latency_ms': self.avg_latency_ms,
            'packet_loss_ratio': self.packet_loss_ratio,
            'connectivity_coeff': self.connectivity_coeff,
            'num_agents': self.num_agents
        }
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)

def main(args=None):
    rclpy.init(args=args)
    node = ExperimentLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.finalize()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
