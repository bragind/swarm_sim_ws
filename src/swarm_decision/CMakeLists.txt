cmake_minimum_required(VERSION 3.8)
project(swarm_decision)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})

# Явная установка Python-скриптов в lib/ (обязательно для ROS 2)
install(PROGRAMS
  ${PROJECT_NAME}/perception_node.py
  ${PROJECT_NAME}/sensor_fusion_node.py
  ${PROJECT_NAME}/task_allocator_node.py
  ${PROJECT_NAME}/decision_core_node.py
  ${PROJECT_NAME}/experiment_logger.py
  ${PROJECT_NAME}/communication_emulator.py
  DESTINATION lib/${PROJECT_NAME}
)
ament_package()
