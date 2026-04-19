cmake_minimum_required(VERSION 3.8)
project(swarm_perception)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(swarm_perception)
install(PROGRAMS
  swarm_perception/perception_node.py
  swarm_perception/sensor_fusion_node.py
  DESTINATION lib/swarm_perception
)
ament_package()
