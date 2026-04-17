cmake_minimum_required(VERSION 3.8)
project(swarm_planning)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(swarm_msgs REQUIRED)
find_package(eigen3_cmake_module REQUIRED)
find_package(Eigen3 3.3 REQUIRED MODULE)

# Зависимости tf2
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

# Исполняемые файлы
add_executable(trajectory_planner_node swarm_planning/trajectory_planner_node.cpp)
ament_target_dependencies(trajectory_planner_node 
  rclcpp std_msgs geometry_msgs nav_msgs sensor_msgs swarm_msgs Eigen3 tf2 tf2_ros tf2_geometry_msgs)

add_executable(connectivity_manager_node swarm_planning/connectivity_manager_node.cpp)
ament_target_dependencies(connectivity_manager_node 
  rclcpp std_msgs geometry_msgs nav_msgs swarm_msgs Eigen3 tf2 tf2_ros)

# Подключение локальных заголовков
target_include_directories(trajectory_planner_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

target_include_directories(connectivity_manager_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

# Установка
install(TARGETS trajectory_planner_node connectivity_manager_node
  DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/
  DESTINATION include)

ament_package()
