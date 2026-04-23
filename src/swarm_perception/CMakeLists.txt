cmake_minimum_required(VERSION 3.8)
project(swarm_perception)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS
    ${PROJECT_NAME}/perception_node.py
    ${PROJECT_NAME}/sensor_fusion_node.py
    DESTINATION lib/${PROJECT_NAME}
)
ament_package()
