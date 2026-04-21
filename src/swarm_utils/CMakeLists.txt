cmake_minimum_required(VERSION 3.8)
project(swarm_utils)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS
  swarm_utils/experiment_logger.py
  swarm_utils/communication_emulator.py
  swarm_utils/metrics_calculator.py
  swarm_utils/swarm_state_publisher.py
  DESTINATION lib/${PROJECT_NAME}
)
ament_package()
