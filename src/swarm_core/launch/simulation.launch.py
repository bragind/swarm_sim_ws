import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition

def generate_launch_description():
    num_uavs = DeclareLaunchArgument('num_uavs', default_value='5')
    num_ugvs = DeclareLaunchArgument('num_ugvs', default_value='3')
    scenario_id = DeclareLaunchArgument('scenario_id', default_value='S1')
    seed = DeclareLaunchArgument('seed', default_value='42')
    use_marl = DeclareLaunchArgument('use_marl', default_value='true')
    gui = DeclareLaunchArgument('gui', default_value='false')
    sim_mode = DeclareLaunchArgument('sim_mode', default_value='logical',
                                     description='Simulation mode: "logical" or "gazebo"')

    swarm_core_dir = get_package_share_directory('swarm_core')
    world_path = os.path.join(swarm_core_dir, 'worlds', 'experimental_polygon.world')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments=[('gz_args', [' -v 4 -r -s ', world_path])],
        condition=IfCondition(PythonExpression(["'", LaunchConfiguration('sim_mode'), "' == 'gazebo'"]))
    )

    logical_sim = Node(
        package='swarm_core',
        executable='logical_swarm_simulator.py',
        name='logical_swarm_simulator',
        parameters=[{
            'num_uavs': LaunchConfiguration('num_uavs'),
            'num_ugvs': LaunchConfiguration('num_ugvs'),
        }],
        output='screen',
        condition=IfCondition(PythonExpression(["'", LaunchConfiguration('sim_mode'), "' == 'logical'"]))
    )

    perception = Node(
        package='swarm_perception', executable='perception_node.py', name='perception',
        output='screen'
    )
    fusion = Node(
        package='swarm_perception', executable='sensor_fusion_node.py', name='sensor_fusion',
        output='screen'
    )
    task_alloc = Node(
        package='swarm_decision', executable='task_allocator_node.py', name='task_allocator',
        parameters=[{'scenario_id': LaunchConfiguration('scenario_id')}],
        output='screen'
    )
    decision = Node(
        package='swarm_decision', executable='decision_core_node.py', name='decision_core',
        parameters=[{
            'use_marl': LaunchConfiguration('use_marl'),
            'model_path': '',
            'dec_pomdp_horizon': 10,
            'exploration_rate': 0.1
        }],
        output='screen'
    )
    planner = Node(
        package='swarm_planning', executable='trajectory_planner_node', name='trajectory_planner',
        parameters=[{'max_velocity': 3.5, 'min_obstacle_distance': 1.0}],
        output='screen'
    )
    conn_mgr = Node(
        package='swarm_planning', executable='connectivity_manager_node', name='connectivity_manager',
        parameters=[{'communication_range': 100.0, 'min_neighbors': 2}],
        output='screen'
    )
    metrics = Node(
        package='swarm_utils', executable='metrics_calculator.py', name='metrics_calculator',
        output='screen'
    )
    logger = Node(
        package='swarm_utils', executable='experiment_logger.py', name='experiment_logger',
        parameters=[{
            'log_path': os.path.expanduser('~/sim_storage/experiments'),
            'scenario_id': LaunchConfiguration('scenario_id'),
            'seed': LaunchConfiguration('seed'),
            'csv_output': True
        }],
        output='screen'
    )
    comm_emu = Node(
        package='swarm_utils', executable='communication_emulator.py', name='comm_emulator',
        parameters=[{
            'packet_loss_rate': 0.0,
            'latency_mean_ms': 20.0,
            'latency_std_ms': 5.0,
            'enabled': True
        }],
        output='screen'
    )

    # Публикатор состояния роя (для логгера)
    swarm_state_publisher = Node(
        package='swarm_utils',
        executable='swarm_state_publisher.py',
        name='swarm_state_publisher',
        output='screen'
    )

    return LaunchDescription([
        num_uavs, num_ugvs, scenario_id, seed, use_marl, gui, sim_mode,
        gazebo, logical_sim,
        perception, fusion, task_alloc, decision,
        planner, conn_mgr, metrics, logger, comm_emu,
        swarm_state_publisher
    ])