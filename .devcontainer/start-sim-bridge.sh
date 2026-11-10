#!/usr/bin/env bash
# Starts the devcontainer side of the simulator bridge in the background,
# logging to /tmp/sim-bridge.log. Run by postStartCommand; safe to rerun from
# a devcontainer terminal if the bridge has died. See docs/simulation.mdx.
#
# The binary comes from the dev image; the sim-side bridge is sim-bridge.sh.
set -euo pipefail

LOG=/tmp/sim-bridge.log

if pgrep -x zenoh-bridge-ros2dds >/dev/null; then
    echo "sim-bridge already running (log: $LOG)"
    exit 0
fi

setsid -f zenoh-bridge-ros2dds router -l tcp/0.0.0.0:7447 --no-multicast-scouting \
    >"$LOG" 2>&1 </dev/null
echo "sim-bridge started (log: $LOG)"
