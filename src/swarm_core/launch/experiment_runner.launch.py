#!/usr/bin/env python3
"""
Orchestrator for batch experiments. Manages parallel scenario execution and logging.
"""
import os
import yaml
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    swarm_core_dir = get_package_share_directory('swarm_core')
    
    # Load scenario configs
    sim_cfg_path = os.path.join(swarm_core_dir, 'config', 'simulation_config.yaml')
    with open(sim_cfg_path, 'r') as f:
        sim_cfg = yaml.safe_load(f)
    
    # Declare arguments
    scenario_id = DeclareLaunchArgument('scenario_id', default_value='S1')
    num_uavs = DeclareLaunchArgument('num_uavs', default_value='5')
    num_ugvs = DeclareLaunchArgument('num_ugvs', default_value='3')
    seed = DeclareLaunchArgument('seed', default_value='42')
    use_marl = DeclareLaunchArgument('use_marl', default_value='true')
    
    # Include main simulation
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([PathJoinSubstitution([swarm_core_dir, 'launch', 'simulation.launch.py'])]),
        launch_arguments={
            'scenario_id': LaunchConfiguration('scenario_id'),
            'num_uavs': LaunchConfiguration('num_uavs'),
            'num_ugvs': LaunchConfiguration('num_ugvs'),
            'seed': LaunchConfiguration('seed'),
            'use_marl': LaunchConfiguration('use_marl')
        }.items()
    )
    
    # Batch orchestrator node
    orchestrator = Node(
        package='swarm_utils',
        executable='batch_runner.py',
        name='experiment_orchestrator',
        parameters=[{
            'scenario_config': sim_cfg['scenarios'],
            'max_parallel_runs': sim_cfg['batch']['max_parallel'],
            'log_dir': os.path.expanduser('~/sim_storage/experiments')
        }],
        output='screen'
    )
    
    return LaunchDescription([
        scenario_id, num_uavs, num_ugvs, seed, use_marl,
        sim_launch, orchestrator
    ])