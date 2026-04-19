cmake_minimum_required(VERSION 3.8)
project(swarm_decision)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(swarm_decision)
install(PROGRAMS
  swarm_decision/task_allocator_node.py
  swarm_decision/decision_core_node.py
  DESTINATION lib/swarm_decision
)
ament_package()
