#!/bin/sh
# devcontainer postStartCommand: starts the urc-side sim bridge (see sim-bridge.sh)
# detached, so it outlives the lifecycle hook. Kept in a script because Zed joins
# lifecycle command args with spaces, which breaks string commands that contain any.
setsid -f pixi run sim-bridge > /tmp/sim-bridge.log 2>&1 < /dev/null
