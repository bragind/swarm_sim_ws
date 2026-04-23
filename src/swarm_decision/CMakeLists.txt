cmake_minimum_required(VERSION 3.8)
project(swarm_decision)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS
  swarm_decision/task_allocator_node.py
  swarm_decision/decision_core_node.py
  DESTINATION lib/${PROJECT_NAME}
)
ament_package()
