cmake_minimum_required(VERSION 3.8)
project(can-ak)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(ak-series REQUIRED)

add_executable(can_ak_node src/can-ak.cpp include/can-ak/can-ak.h)
target_compile_features(can_ak_node PRIVATE cxx_std_17)
target_include_directories(
  can_ak_node PRIVATE $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)
# ak_series_lib comes from ak-series's exported targets, under the ak-series::
# namespace. It pulls in libsocketcan and its own include dir transitively.
target_link_libraries(can_ak_node PRIVATE rclcpp::rclcpp
                                          ak-series::ak_series_lib)

# Required for `ros2 run can-ak can_ak_node` to find the executable
install(TARGETS can_ak_node DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights comment the
  # line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo) comment the line
  # when this package is in a git repo and when a copyright and license is added
  # to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
