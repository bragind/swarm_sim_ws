cmake_minimum_required(VERSION 3.8)
project(swarm_utils)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS
    ${PROJECT_NAME}/experiment_logger.py
    ${PROJECT_NAME}/communication_emulator.py
    ${PROJECT_NAME}/metrics_calculator.py
    ${PROJECT_NAME}/mission_supervisor.py
    ${PROJECT_NAME}/swarm_state_publisher.py
    DESTINATION lib/${PROJECT_NAME}
)
ament_package()
