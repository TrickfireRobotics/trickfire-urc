#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/.."

readonly launch_package="${LAUNCH_PACKAGE:-rover_launch}"
readonly launch_file="${LAUNCH_FILE:-robot.launch.py}"

if [[ ! -f install/setup.bash ]]; then
    echo "No workspace overlay found. Run 'make build' first." >&2
    exit 1
fi

export RCUTILS_COLORIZED_OUTPUT=1
source "/opt/ros/${ROS_DISTRO:?ROS_DISTRO must be set}/setup.bash"
source install/setup.bash

if ! ros2 pkg prefix "$launch_package" >/dev/null 2>&1; then
    echo "Launch package '$launch_package' is not installed." >&2
    echo "Set LAUNCH_PACKAGE and LAUNCH_FILE after adding the rover launch package:" >&2
    echo "  make launch LAUNCH_PACKAGE=<package> LAUNCH_FILE=<file.launch.py>" >&2
    exit 1
fi

exec ros2 launch "$launch_package" "$launch_file"
