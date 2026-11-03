cmake_minimum_required(VERSION 3.10)
project(navigation_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(geographic_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/NavigateToGPS.action"
  "action/NavigateToTarget.action"
  DEPENDENCIES geographic_msgs geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
