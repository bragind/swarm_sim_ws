#!/usr/bin/env python3
"""
Полнофункциональный логический симулятор роя агентов.
Генерирует состояния UAV и UGV, цели миссии, отслеживает столкновения, энергопотребление
и эмулирует сетевой трафик для проверки метрик.
"""

import rclpy
from rclpy.node import Node
from swarm_msgs.msg import SwarmState, AgentState
from geometry_msgs.msg import Point, Quaternion, Twist, PoseStamped
from std_msgs.msg import Float64, Bool
import math
import random
import time

class LogicalSwarmSimulator(Node):
    def __init__(self):
        super().__init__('logical_swarm_simulator')
        
        # Параметры
        self.declare_parameter('num_uavs', 5)
        self.declare_parameter('num_ugvs', 3)
        self.declare_parameter('update_rate', 10.0)  # Hz
        self.declare_parameter('collision_distance', 2.0)  # meters
        self.declare_parameter('energy_factor', 0.001)    # Wh per (m/s)^2 per second
        
        self.num_uavs = self.get_parameter('num_uavs').value
        self.num_ugvs = self.get_parameter('num_ugvs').value
        self.update_rate = self.get_parameter('update_rate').value
        self.collision_dist = self.get_parameter('collision_distance').value
        self.energy_factor = self.get_parameter('energy_factor').value
        
        # Состояние симуляции
        self.time = 0.0
        self.collision_count = 0
        self.total_energy = 0.0
        self.success_flag = False
        self.target_reached = False
        
        # Инициализация позиций агентов
        self.uav_positions = []
        self.ugv_positions = []
        for i in range(self.num_uavs):
            angle = 2.0 * math.pi * i / max(1, self.num_uavs)
            self.uav_positions.append([30.0 * math.cos(angle), 30.0 * math.sin(angle), 10.0])
        for i in range(self.num_ugvs):
            self.ugv_positions.append([15.0 * i, 40.0, 0.0])
        
        # Цели миссии (случайные точки в пределах мира)
        self.targets = []
        for _ in range(3):
            target = PoseStamped()
            target.header.frame_id = 'map'
            target.pose.position.x = random.uniform(-40, 40)
            target.pose.position.y = random.uniform(-20, 60)
            target.pose.position.z = 0.0
            target.pose.orientation.w = 1.0
            self.targets.append(target)
        
        # Публикации
        self.state_pub = self.create_publisher(SwarmState, '/swarm/state', 10)
        self.target_pub = self.create_publisher(PoseStamped, '/swarm/target', 10)
        self.collision_pub = self.create_publisher(Float64, '/swarm/collisions', 10)
        self.energy_pub = self.create_publisher(Float64, '/swarm/total_energy', 10)
        self.success_pub = self.create_publisher(Bool, '/swarm/success', 10)
        
        # Для эмуляции трафика: слушаем топики, куда узлы отправляют команды
        # и отвечаем фиктивными сообщениями, чтобы communication_emulator считал задержки/потери
        self.create_subscription(PoseStamped, '/swarm/command', self.command_callback, 10)
        self.cmd_received = False
        
        # Таймеры
        self.timer = self.create_timer(1.0/self.update_rate, self.publish_state)
        self.target_timer = self.create_timer(5.0, self.publish_targets)  # обновление целей каждые 5 сек
        self.traffic_timer = self.create_timer(0.5, self.generate_traffic)  # эмуляция обмена сообщениями
        
        self.get_logger().info(f'Full logical simulator started: {self.num_uavs} UAVs, {self.num_ugvs} UGVs')
    
    def command_callback(self, msg):
        self.cmd_received = True
    
    def generate_traffic(self):
        """Периодически публикует фиктивные команды, чтобы communication_emulator имел трафик."""
        cmd = PoseStamped()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = 'map'
        cmd.pose.position.x = random.uniform(-10, 10)
        cmd.pose.position.y = random.uniform(-10, 10)
        # Публикуем в топик, который проходит через эмулятор связи
        self.target_pub.publish(cmd)  # используем существующий publisher для генерации трафика
    
    def publish_targets(self):
        """Публикует текущую цель для роя."""
        if self.targets:
            target = random.choice(self.targets)
            target.header.stamp = self.get_clock().now().to_msg()
            self.target_pub.publish(target)
    
    def check_collisions(self, positions):
        """Проверяет попарные расстояния и увеличивает счётчик столкновений."""
        n = len(positions)
        for i in range(n):
            for j in range(i+1, n):
                dx = positions[i][0] - positions[j][0]
                dy = positions[i][1] - positions[j][1]
                dz = positions[i][2] - positions[j][2]
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist < self.collision_dist:
                    self.collision_count += 1
                    self.get_logger().debug(f'Collision between {i} and {j}')
    
    def calculate_energy(self, velocities):
        """Энергия = сумма квадратов скоростей * коэффициент."""
        energy = 0.0
        for v in velocities:
            speed_sq = v[0]**2 + v[1]**2 + v[2]**2
            energy += speed_sq * self.energy_factor
        self.total_energy += energy
        return energy
    
    def check_success(self, positions):
        """Если хотя бы один агент близко к любой цели, миссия успешна."""
        if not self.targets:
            return
        for pos in positions:
            for target in self.targets:
                dx = pos[0] - target.pose.position.x
                dy = pos[1] - target.pose.position.y
                dz = pos[2] - target.pose.position.z
                if math.sqrt(dx*dx + dy*dy + dz*dz) < 5.0:
                    self.success_flag = True
                    self.target_reached = True
                    return
    
    def publish_state(self):
        self.time += 1.0/self.update_rate
        
        msg = SwarmState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        
        # Списки для хранения позиций и скоростей для проверки столкновений и энергии
        all_positions = []
        all_velocities = []
        
        # Генерация UAV
        radius_uav = 30.0
        center_x, center_y = 0.0, 0.0
        for i in range(self.num_uavs):
            agent = AgentState()
            agent.id = f'uav_{i}'
            agent.type = 'uav'
            
            # Движение по окружности с небольшим шумом
            angle = 2.0 * math.pi * i / max(1, self.num_uavs) + 0.1 * self.time
            pos_x = center_x + radius_uav * math.cos(angle)
            pos_y = center_y + radius_uav * math.sin(angle)
            pos_z = 10.0 + 2.0 * math.sin(0.3 * self.time)
            
            agent.position.x = pos_x
            agent.position.y = pos_y
            agent.position.z = pos_z
            all_positions.append([pos_x, pos_y, pos_z])
            
            # Скорость (производная от позиции)
            vx = -radius_uav * 0.1 * math.sin(angle)
            vy = radius_uav * 0.1 * math.cos(angle)
            vz = 0.6 * math.cos(0.3 * self.time)
            agent.velocity.linear.x = vx
            agent.velocity.linear.y = vy
            agent.velocity.linear.z = vz
            all_velocities.append([vx, vy, vz])
            
            # Ориентация
            yaw = angle + math.pi/2
            agent.orientation = self.yaw_to_quaternion(yaw)
            
            agent.battery_level = max(20.0, 100.0 - 5.0 * (self.time % 60.0))
            agent.status = 'active'
            msg.agents.append(agent)
        
        # Генерация UGV
        for i in range(self.num_ugvs):
            agent = AgentState()
            agent.id = f'ugv_{i}'
            agent.type = 'ugv'
            
            t = self.time
            offset_x = 15.0 * i
            pos_x = 20.0 * math.sin(0.05 * t + i*1.5) + offset_x
            pos_y = 15.0 * math.cos(0.03 * t + i) + 40.0
            pos_z = 0.0
            
            agent.position.x = pos_x
            agent.position.y = pos_y
            agent.position.z = pos_z
            all_positions.append([pos_x, pos_y, pos_z])
            
            vx = 20.0 * 0.05 * math.cos(0.05*t + i*1.5)
            vy = -15.0 * 0.03 * math.sin(0.03*t + i)
            vz = 0.0
            agent.velocity.linear.x = vx
            agent.velocity.linear.y = vy
            agent.velocity.linear.z = vz
            all_velocities.append([vx, vy, vz])
            
            yaw = math.atan2(vy, vx)
            agent.orientation = self.yaw_to_quaternion(yaw)
            
            agent.battery_level = max(30.0, 100.0 - 3.0 * (self.time % 80.0))
            agent.status = 'active'
            msg.agents.append(agent)
        
        # Коэффициент связности (имитация)
        msg.connectivity_coefficient = 0.7 + 0.2 * math.sin(0.1 * self.time)
        
        # Публикация состояния
        self.state_pub.publish(msg)
        
        # Проверка столкновений и успеха
        self.check_collisions(all_positions)
        self.check_success(all_positions)
        
        # Расчёт энергии
        energy_this_step = self.calculate_energy(all_velocities)
        
        # Публикация метрик
        self.collision_pub.publish(Float64(data=float(self.collision_count)))
        self.energy_pub.publish(Float64(data=self.total_energy))
        self.success_pub.publish(Bool(data=self.success_flag))
    
    def yaw_to_quaternion(self, yaw):
        q = Quaternion()
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(yaw / 2.0)
        q.w = math.cos(yaw / 2.0)
        return q

def main(args=None):
    rclpy.init(args=args)
    node = LogicalSwarmSimulator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
