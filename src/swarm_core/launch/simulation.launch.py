import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    swarm_core_dir = get_package_share_directory('swarm_core')
    try:
        swarm_decision_dir = get_package_share_directory('swarm_decision')
    except Exception:
        swarm_decision_dir = ''

    world_path = os.path.join(swarm_core_dir, 'worlds', 'wkr_test_field_light.world')
    default_model = os.path.join(os.getcwd(), 'models', 'marl', 'wkr_qmix_policy.pt')

    args = [
        DeclareLaunchArgument('scenario_id', default_value='S1'),
        DeclareLaunchArgument('architecture', default_value='marl_decpomdp'),
        DeclareLaunchArgument('architecture_id', default_value=''),
        DeclareLaunchArgument('seed', default_value='42'),
        DeclareLaunchArgument('num_agents', default_value='8'),
        DeclareLaunchArgument('num_uavs', default_value='5'),
        DeclareLaunchArgument('num_ugvs', default_value='3'),
        DeclareLaunchArgument('use_marl', default_value='true'),
        DeclareLaunchArgument('use_dec_pomdp', default_value='true'),
        DeclareLaunchArgument('marl_model_path', default_value=default_model),
        DeclareLaunchArgument('mission_timeout_s', default_value='120.0'),
        DeclareLaunchArgument('logger_timeout_s', default_value='125.0'),
        DeclareLaunchArgument('experiment_profile', default_value='full'),
        DeclareLaunchArgument('success_criteria_profile', default_value='full'),
        DeclareLaunchArgument('simulation_mode', default_value='gazebo_headless'),
        DeclareLaunchArgument('headless_fast', default_value='false'),
        DeclareLaunchArgument('headless', default_value='true'),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('sim_mode', default_value='logical'),
        DeclareLaunchArgument('log_dir', default_value=os.path.expanduser('~/sim_storage/experiments')),
        DeclareLaunchArgument('run_id', default_value=''),
        DeclareLaunchArgument('packet_loss', default_value='0.0'),
        DeclareLaunchArgument('latency_ms', default_value='20.0'),
        DeclareLaunchArgument('latency_std_ms', default_value='5.0'),
        DeclareLaunchArgument('comm_range', default_value='55.0'),
        DeclareLaunchArgument('obstacle_density', default_value='0.35'),
        DeclareLaunchArgument('dynamic_obstacles', default_value='2'),
        DeclareLaunchArgument('agent_failure_ratio', default_value='0.0'),
        DeclareLaunchArgument('compute_delay_ms', default_value='0.0'),
        DeclareLaunchArgument('coverage_threshold', default_value='0.75'),
        DeclareLaunchArgument('connectivity_threshold', default_value='0.55'),
        DeclareLaunchArgument('min_active_agents', default_value='6'),
        DeclareLaunchArgument('marl_model_exists', default_value='false'),
        DeclareLaunchArgument('marl_model_allowed_for_proof', default_value='false'),
        DeclareLaunchArgument('marl_model_type', default_value='unknown'),
        DeclareLaunchArgument('world_file', default_value=world_path),
    ]

    architecture = PythonExpression([
        "'", LaunchConfiguration('architecture'), "' if '", LaunchConfiguration('architecture'),
        "' != '' else '", LaunchConfiguration('architecture_id'), "'"
    ])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments=[('gz_args', [
            ' -v 2 -r -s ', LaunchConfiguration('world_file'),
            PythonExpression(["' --gui' if '", LaunchConfiguration('gui'), "' == 'true' else ''"])
        ])],
        condition=IfCondition(PythonExpression(["'", LaunchConfiguration('sim_mode'), "' == 'gazebo'"]))
    )

    common = {
        'scenario_id': LaunchConfiguration('scenario_id'),
        'architecture': architecture,
        'seed': LaunchConfiguration('seed'),
        'num_agents': LaunchConfiguration('num_agents'),
        'num_uavs': LaunchConfiguration('num_uavs'),
        'num_ugvs': LaunchConfiguration('num_ugvs'),
    }

    swarm_state_publisher = Node(
        package='swarm_utils',
        executable='swarm_state_publisher.py',
        name='swarm_state_publisher',
        parameters=[{
            **common,
            'simulation_mode': LaunchConfiguration('simulation_mode'),
            'headless_fast': LaunchConfiguration('headless_fast'),
            'agent_failure_ratio': LaunchConfiguration('agent_failure_ratio'),
        }],
        output='screen'
    )

    task_alloc = Node(
        package='swarm_decision',
        executable='task_allocator_node.py',
        name='task_allocator',
        parameters=[common],
        output='screen'
    )

    decision = Node(
        package='swarm_decision',
        executable='decision_core_node.py',
        name='decision_core',
        parameters=[{
            **common,
            'run_id': LaunchConfiguration('run_id'),
            'architecture_id': architecture,
            'use_marl': LaunchConfiguration('use_marl'),
            'use_dec_pomdp': LaunchConfiguration('use_dec_pomdp'),
            'marl_model_path': LaunchConfiguration('marl_model_path'),
            'model_path': LaunchConfiguration('marl_model_path'),
            'marl_model_exists': LaunchConfiguration('marl_model_exists'),
            'marl_model_allowed_for_proof': LaunchConfiguration('marl_model_allowed_for_proof'),
            'marl_model_type': LaunchConfiguration('marl_model_type'),
            'communication_range': LaunchConfiguration('comm_range'),
            'compute_delay_ms': LaunchConfiguration('compute_delay_ms'),
        }],
        output='screen'
    )

    metrics = Node(
        package='swarm_utils',
        executable='metrics_calculator.py',
        name='metrics_calculator',
        parameters=[{
            **common,
            'packet_loss': LaunchConfiguration('packet_loss'),
            'latency_ms': LaunchConfiguration('latency_ms'),
            'comm_range': LaunchConfiguration('comm_range'),
            'obstacle_density': LaunchConfiguration('obstacle_density'),
            'agent_failure_ratio': LaunchConfiguration('agent_failure_ratio'),
            'simulation_mode': LaunchConfiguration('simulation_mode'),
        }],
        output='screen'
    )

    supervisor = Node(
        package='swarm_utils',
        executable='mission_supervisor.py',
        name='mission_supervisor',
        parameters=[{
            **common,
            'run_id': LaunchConfiguration('run_id'),
            'mission_timeout_s': LaunchConfiguration('mission_timeout_s'),
            'experiment_profile': LaunchConfiguration('experiment_profile'),
            'success_criteria_profile': LaunchConfiguration('success_criteria_profile'),
            'coverage_threshold': LaunchConfiguration('coverage_threshold'),
            'connectivity_threshold': LaunchConfiguration('connectivity_threshold'),
            'min_active_agents': LaunchConfiguration('min_active_agents'),
        }],
        output='screen'
    )

    logger = Node(
        package='swarm_utils',
        executable='experiment_logger.py',
        name='experiment_logger',
        parameters=[{
            **common,
            'run_id': LaunchConfiguration('run_id'),
            'log_dir': LaunchConfiguration('log_dir'),
            'mission_timeout_s': LaunchConfiguration('mission_timeout_s'),
            'logger_timeout_s': LaunchConfiguration('logger_timeout_s'),
            'experiment_profile': LaunchConfiguration('experiment_profile'),
            'success_criteria_profile': LaunchConfiguration('success_criteria_profile'),
            'simulation_mode': LaunchConfiguration('simulation_mode'),
            'marl_model_path': LaunchConfiguration('marl_model_path'),
            'marl_model_exists': LaunchConfiguration('marl_model_exists'),
            'marl_model_allowed_for_proof': LaunchConfiguration('marl_model_allowed_for_proof'),
            'marl_model_type': LaunchConfiguration('marl_model_type'),
        }],
        output='screen'
    )

    comm_emu = Node(
        package='swarm_utils',
        executable='communication_emulator.py',
        name='comm_emulator',
        parameters=[{
            'scenario_id': LaunchConfiguration('scenario_id'),
            'seed': LaunchConfiguration('seed'),
            'packet_loss': LaunchConfiguration('packet_loss'),
            'latency_ms': LaunchConfiguration('latency_ms'),
            'latency_std_ms': LaunchConfiguration('latency_std_ms'),
            'enabled': True,
        }],
        output='screen'
    )

    return LaunchDescription(args + [
        gazebo,
        swarm_state_publisher,
        task_alloc,
        decision,
        metrics,
        supervisor,
        logger,
        comm_emu,
    ])
