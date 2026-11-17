#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/.."

source "/opt/ros/${ROS_DISTRO:?ROS_DISTRO must be set}/setup.bash"

colcon build \
    --symlink-install \
    --base-paths src-platform src-autonomy \
    --packages-ignore zed_components zed_debug zed_ros2 zed_wrapper \
    --cmake-args \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
