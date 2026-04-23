import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition


def generate_launch_description():
    # === Базовые параметры ===
    num_uavs = DeclareLaunchArgument('num_uavs', default_value='5',
                                     description='Number of UAV agents')
    num_ugvs = DeclareLaunchArgument('num_ugvs', default_value='3',
                                     description='Number of UGV agents')
    scenario_id = DeclareLaunchArgument('scenario_id', default_value='S1',
                                        description='Scenario ID: S1-S6')
    seed = DeclareLaunchArgument('seed', default_value='42',
                                 description='Random seed for reproducibility')
    
    # === Параметры архитектуры управления (НОВОЕ) ===
    architecture_id = DeclareLaunchArgument(
        'architecture_id', 
        default_value='marl_decpomdp',
        description='Control architecture: central_a_star|reactive|rule_dec|marl_decpomdp'
    )
    use_marl = DeclareLaunchArgument('use_marl', default_value='true',
                                     description='Enable MARL correction')
    use_dec_pomdp = DeclareLaunchArgument('use_dec_pomdp', default_value='true',
                                          description='Enable Dec-POMDP solver')
    planner_mode = DeclareLaunchArgument(
        'planner_mode',
        default_value='hybrid',
        description='Planning mode: central|reactive|rule_based|hybrid'
    )
    
    # === Параметры симуляции ===
    gui = DeclareLaunchArgument('gui', default_value='false',
                                description='Enable Gazebo GUI')
    sim_mode = DeclareLaunchArgument('sim_mode', default_value='logical',
                                     description='Simulation mode: "logical" or "gazebo"')
    
    # === Параметры коммуникационной среды (НОВОЕ) ===
    packet_loss_rate = DeclareLaunchArgument('packet_loss_rate', default_value='0.0',
                                             description='Packet loss probability [0.0-1.0]')
    latency_mean_ms = DeclareLaunchArgument('latency_mean_ms', default_value='20.0',
                                            description='Mean communication latency (ms)')
    latency_std_ms = DeclareLaunchArgument('latency_std_ms', default_value='5.0',
                                           description='Latency standard deviation (ms)')
    comm_range = DeclareLaunchArgument('comm_range', default_value='100.0',
                                       description='Communication range (meters)')

    swarm_core_dir = get_package_share_directory('swarm_core')
    world_path = os.path.join(swarm_core_dir, 'worlds', 'experimental_polygon.world')

    # === Gazebo симуляция ===
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments=[('gz_args', [' -v 4 -r -s ', world_path, 
                                       PythonExpression(["' --gui' if '", 
                                                        LaunchConfiguration('gui'), 
                                                        "' == 'true' else ''"])])],
        condition=IfCondition(PythonExpression(["'", LaunchConfiguration('sim_mode'), "' == 'gazebo'"]))
    )

    # === Логическая симуляция ===
    logical_sim = Node(
        package='swarm_core',
        executable='logical_swarm_simulator.py',
        name='logical_swarm_simulator',
        parameters=[{
            'num_uavs': LaunchConfiguration('num_uavs'),
            'num_ugvs': LaunchConfiguration('num_ugvs'),
            'scenario_id': LaunchConfiguration('scenario_id'),
            'seed': LaunchConfiguration('seed'),
        }],
        output='screen',
        condition=IfCondition(PythonExpression(["'", LaunchConfiguration('sim_mode'), "' == 'logical'"]))
    )

    # === Модуль восприятия ===
    perception = Node(
        package='swarm_perception', executable='perception_node.py', name='perception',
        parameters=[{'scenario_id': LaunchConfiguration('scenario_id')}],
        output='screen'
    )
    fusion = Node(
        package='swarm_perception', executable='sensor_fusion_node.py', name='sensor_fusion',
        output='screen'
    )

    # === Распределение задач ===
    task_alloc = Node(
        package='swarm_decision', executable='task_allocator_node.py', name='task_allocator',
        parameters=[{
            'scenario_id': LaunchConfiguration('scenario_id'),
            'planner_mode': LaunchConfiguration('planner_mode'),  # НОВОЕ
        }],
        output='screen'
    )

    # === Ядро принятия решений (ОБНОВЛЕНО) ===
    decision = Node(
        package='swarm_decision', executable='decision_core_node.py', name='decision_core',
        parameters=[{
            'architecture_id': LaunchConfiguration('architecture_id'),  # НОВОЕ
            'use_marl': LaunchConfiguration('use_marl'),
            'use_dec_pomdp': LaunchConfiguration('use_dec_pomdp'),      # НОВОЕ
            'planner_mode': LaunchConfiguration('planner_mode'),        # НОВОЕ
            'model_path': '',
            'dec_pomdp_horizon': 10,
            'exploration_rate': 0.1,
            'seed': LaunchConfiguration('seed'),
        }],
        output='screen'
    )

    # === Планировщик траекторий (ОБНОВЛЕНО) ===
    planner = Node(
        package='swarm_planning', executable='trajectory_planner_node', name='trajectory_planner',
        parameters=[{
            'max_velocity': 3.5, 
            'min_obstacle_distance': 1.0,
            'planner_mode': LaunchConfiguration('planner_mode'),  # НОВОЕ
            'scenario_id': LaunchConfiguration('scenario_id'),    # НОВОЕ
        }],
        output='screen'
    )

    # === Менеджер связности (ОБНОВЛЕНО) ===
    conn_mgr = Node(
        package='swarm_planning', executable='connectivity_manager_node', name='connectivity_manager',
        parameters=[{
            'communication_range': LaunchConfiguration('comm_range'),  # Динамический параметр
            'min_neighbors': 2,
            'scenario_id': LaunchConfiguration('scenario_id'),
        }],
        output='screen'
    )

    # === Метрики и логирование ===
    metrics = Node(
        package='swarm_utils', executable='metrics_calculator.py', name='metrics_calculator',
        parameters=[{
            'architecture_id': LaunchConfiguration('architecture_id'),
            'scenario_id': LaunchConfiguration('scenario_id'),
        }],
        output='screen'
    )
    logger = Node(
        package='swarm_utils', executable='experiment_logger.py', name='experiment_logger',
        parameters=[{
            'log_path': os.path.expanduser('~/sim_storage/experiments'),
            'scenario_id': LaunchConfiguration('scenario_id'),
            'seed': LaunchConfiguration('seed'),
            'architecture_id': LaunchConfiguration('architecture_id'),  # НОВОЕ
            'csv_output': True
        }],
        output='screen'
    )

    # === Эмулятор коммуникаций (ОБНОВЛЕНО) ===
    comm_emu = Node(
        package='swarm_utils', executable='communication_emulator.py', name='comm_emulator',
        parameters=[{
            'packet_loss_rate': LaunchConfiguration('packet_loss_rate'),   # Динамический
            'latency_mean_ms': LaunchConfiguration('latency_mean_ms'),     # Динамический
            'latency_std_ms': LaunchConfiguration('latency_std_ms'),       # Динамический
            'communication_range': LaunchConfiguration('comm_range'),      # Динамический
            'enabled': True,
            'scenario_id': LaunchConfiguration('scenario_id'),             # Для сценариев S3, S4
        }],
        output='screen'
    )

    # Публикатор состояния роя
    swarm_state_publisher = Node(
        package='swarm_utils',
        executable='swarm_state_publisher.py',
        name='swarm_state_publisher',
        parameters=[{
            'num_uavs': LaunchConfiguration('num_uavs'),
            'num_ugvs': LaunchConfiguration('num_ugvs'),
        }],
        output='screen'
    )

    # === Сбор LaunchDescription ===
    return LaunchDescription([
        # Объявления аргументов
        num_uavs, num_ugvs, scenario_id, seed,
        architecture_id, use_marl, use_dec_pomdp, planner_mode,  # НОВОЕ
        packet_loss_rate, latency_mean_ms, latency_std_ms, comm_range,  # НОВОЕ
        gui, sim_mode,
        
        # Симуляция
        gazebo, logical_sim,
        
        # Пайплайн обработки
        perception, fusion, 
        task_alloc, decision,
        planner, conn_mgr, 
        metrics, logger, comm_emu,
        swarm_state_publisher
    ])