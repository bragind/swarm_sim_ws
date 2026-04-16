#!/usr/bin/env python3
"""
Main launch file for swarm simulation.
Implements architecture from Chapter 2 and algorithms from Chapter 3.
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Declare arguments
    num_uavs = DeclareLaunchArgument('num_uavs', default_value='5', 
                                      description='Number of UAV agents')
    num_ugvs = DeclareLaunchArgument('num_ugvs', default_value='3',
                                      description='Number of UGV agents')
    scenario_id = DeclareLaunchArgument('scenario_id', default_value='S1',
                                         description='Experiment scenario ID')
    seed = DeclareLaunchArgument('seed', default_value='42',
                                  description='Random seed for reproducibility')
    use_marl = DeclareLaunchArgument('use_marl', default_value='true',
                                      description='Enable MARL decision module')
    
    # Get package paths
    swarm_core_dir = get_package_share_directory('swarm_core')
    swarm_perception_dir = get_package_share_directory('swarm_perception')
    swarm_decision_dir = get_package_share_directory('swarm_decision')
    swarm_planning_dir = get_package_share_directory('swarm_planning')
    
    # Gazebo simulation
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments={
            'gz_args': '-r experimental_polygon.world',
            'on_shutdown_shutdown': 'true'
        }.items()
    )
    
    # Spawn agents
    spawn_agents = Node(
        package='swarm_core',
        executable='spawn_agents.py',
        name='agent_spawner',
        parameters=[{
            'num_uavs': LaunchConfiguration('num_uavs'),
            'num_ugvs': LaunchConfiguration('num_ugvs'),
            'seed': LaunchConfiguration('seed')
        }],
        output='screen'
    )
    
    # Perception nodes (Python)
    perception_node = Node(
        package='swarm_perception',
        executable='perception_node',
        name='perception',
        namespace='agent_0',
        parameters=[PathJoinSubstitution([swarm_perception_dir, 'config', 'perception.yaml'])],
        output='screen'
    )
    
    sensor_fusion_node = Node(
        package='swarm_perception',
        executable='sensor_fusion_node',
        name='sensor_fusion',
        namespace='agent_0',
        output='screen'
    )
    
    # Decision nodes (Python with MARL)
    task_allocator = Node(
        package='swarm_decision',
        executable='task_allocator_node',
        name='task_allocator',
        parameters=[{
            'scenario_id': LaunchConfiguration('scenario_id'),
            'use_auction': True,
            'utility_weights': [0.4, 0.3, 0.2, 0.1]  # time, energy, safety, connectivity
        }],
        output='screen'
    )
    
    decision_core = Node(
        package='swarm_decision',
        executable='decision_core_node',
        name='decision_core',
        parameters=[{
            'use_marl': LaunchConfiguration('use_marl'),
            'model_path': PathJoinSubstitution([swarm_decision_dir, 'models', 'trained_policy.pt']),
            'dec_pomdp_horizon': 10,
            'exploration_rate': 0.1
        }],
        output='screen'
    )
    
    # Planning nodes (C++ for performance)
    trajectory_planner = Node(
        package='swarm_planning',
        executable='trajectory_planner_node',
        name='trajectory_planner',
        namespace='agent_0',
        parameters=[{
            'planner_type': 'hybrid_astar_mpc',
            'max_velocity': 3.5,
            'min_obstacle_distance': 1.0
        }],
        output='screen'
    )
    
    connectivity_manager = Node(
        package='swarm_planning',
        executable='connectivity_manager_node',
        name='connectivity_manager',
        parameters=[{
            'communication_range': 100.0,
            'min_neighbors': 2,
            'recovery_strategy': 'flocking'
        }],
        output='screen'
    )
    
    # Experiment logger
    experiment_logger = Node(
        package='swarm_utils',
        executable='experiment_logger.py',
        name='experiment_logger',
        parameters=[{
            'log_path': os.path.expanduser('~/sim_storage/experiments'),
            'scenario_id': LaunchConfiguration('scenario_id'),
            'metrics': ['mission_time', 'collisions', 'energy', 'connectivity'],
            'csv_output': True
        }],
        output='screen'
    )
    
    # Communication emulator (for degradation scenarios)
    comm_emulator = Node(
        package='swarm_utils',
        executable='communication_emulator.py',
        name='comm_emulator',
        parameters=[{
            'packet_loss_rate': 0.0,
            'latency_mean_ms': 20.0,
            'latency_std_ms': 5.0,
            'enabled': LaunchConfiguration('scenario_id').perform(LaunchConfiguration('__context__')) != 'S1'
        }],
        output='screen'
    )
    
    return LaunchDescription([
        num_uavs,
        num_ugvs,
        scenario_id,
        seed,
        use_marl,
        gazebo,
        spawn_agents,
        perception_node,
        sensor_fusion_node,
        task_allocator,
        decision_core,
        trajectory_planner,
        connectivity_manager,
        experiment_logger,
        comm_emulator
    ])