cmake_minimum_required(VERSION 3.8)
project(swarm_decision)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS
    ${PROJECT_NAME}/task_allocator_node.py
    ${PROJECT_NAME}/decision_core_node.py
    DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY models DESTINATION share/${PROJECT_NAME})
ament_package()
