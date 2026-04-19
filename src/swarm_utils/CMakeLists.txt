cmake_minimum_required(VERSION 3.8)
project(swarm_utils)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(swarm_utils)
install(PROGRAMS
  swarm_utils/experiment_logger.py
  swarm_utils/communication_emulator.py
  DESTINATION lib/swarm_utils
)
ament_package()
