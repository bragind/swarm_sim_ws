cmake_minimum_required(VERSION 3.8)
project(swarm_planning)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(swarm_msgs REQUIRED)
find_package(Eigen3 REQUIRED)

add_executable(trajectory_planner_node swarm_planning/trajectory_planner_node.cpp)
ament_target_dependencies(trajectory_planner_node rclcpp geometry_msgs nav_msgs sensor_msgs swarm_msgs Eigen3)

add_executable(connectivity_manager_node swarm_planning/connectivity_manager_node.cpp)
ament_target_dependencies(connectivity_manager_node rclcpp geometry_msgs nav_msgs swarm_msgs Eigen3)

target_include_directories(trajectory_planner_node PUBLIC include)
target_include_directories(connectivity_manager_node PUBLIC include)

install(TARGETS trajectory_planner_node connectivity_manager_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include/)

ament_package()