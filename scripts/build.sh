#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/.."

source "/opt/ros/${ROS_DISTRO:?ROS_DISTRO must be set}/setup.bash"

# submodule only used on the rover
# this is to remove useles build warning in dev
zed_ignore_args=()
if [ -n "$(ls -A src-platform/zed-ros2-wrapper 2>/dev/null)" ]; then
    zed_ignore_args=(--packages-ignore zed_components zed_debug zed_ros2 zed_wrapper)
fi

colcon build \
    --symlink-install \
    --base-paths src-platform src-autonomy \
    "${zed_ignore_args[@]}" \
    --cmake-args \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
