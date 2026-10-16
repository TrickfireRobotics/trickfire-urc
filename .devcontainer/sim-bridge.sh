#!/usr/bin/env bash
# Connects the simulator's ROS 2 graph to the trickfire-urc container.
# DDS multicast discovery can't cross the Docker boundary, so a zenoh bridge
# runs on each side and forwards topics/services/actions over TCP port 7447.
#
# Run from a HOST terminal, not inside the devcontainer. The urc-side bridge
# (sim-bridge compose service) starts with the devcontainer automatically.
#
#   sim-bridge.sh native   run the sim-side bridge on this host (sim via pixi)
#   sim-bridge.sh docker   run the sim-side bridge in the sim's container
#   sim-bridge.sh up|down  start/stop the urc-side bridge (only needed when
#                          the devcontainer was started without it)
# Extra args to native/docker are passed to zenoh-bridge-ros2dds.
#
# Env: ROS_DOMAIN_ID (default 0), SIM_CONTAINER (default simulations),
#      ZENOH_ENDPOINT (override where the sim-side bridge connects).
set -euo pipefail

# Must match the sim-bridge image tag in docker-compose.yml.
VERSION=1.10.1
IMAGE="eclipse/zenoh-bridge-ros2dds:${VERSION}"
URC_CONTAINER=trickfire-urc

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export ROS_DISTRO=jazzy

log() { printf "\033[1;36m[sim-bridge]\033[0m %s\n" "$1"; }
die() {
	printf "\033[1;31m[sim-bridge]\033[0m %s\n" "$1" >&2
	exit 1
}

# The sim-side bridge must see the sim's DDS traffic, so it can't run in here.
if [ -f /.dockerenv ] || [ -f /run/.containerenv ]; then
	die "run this from a host terminal (where the sim runs), not inside a container"
fi

# Join the devcontainer's compose project so the bridge shares its network.
compose() {
	local project
	command -v docker >/dev/null || die "docker CLI not found on this host"
	project="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' \
		"$URC_CONTAINER" 2>/dev/null)" ||
		die "container '$URC_CONTAINER' is not running - open the devcontainer first"
	docker compose -p "$project" -f "$script_dir/docker-compose.yml" "$@"
}

native_target() {
	case "$(uname -s)/$(uname -m)" in
	Darwin/arm64) echo aarch64-apple-darwin ;;
	Darwin/x86_64) echo x86_64-apple-darwin ;;
	Linux/x86_64) echo x86_64-unknown-linux-gnu ;;
	Linux/aarch64 | Linux/arm64) echo aarch64-unknown-linux-gnu ;;
	*) die "no native bridge for $(uname -sm) - run the sim in Docker and use 'docker' mode" ;;
	esac
}

native_bin() {
	local target dir zip url
	target="$(native_target)"
	dir="${XDG_CACHE_HOME:-$HOME/.cache}/trickfire/zenoh-bridge-ros2dds/$VERSION"
	if [ ! -x "$dir/zenoh-bridge-ros2dds" ]; then
		zip="zenoh-plugin-ros2dds-${VERSION}-${target}-standalone.zip"
		url="https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds/releases/download/${VERSION}/${zip}"
		log "downloading $zip" >&2
		mkdir -p "$dir"
		curl -fsSL "$url" -o "$dir/$zip"
		unzip -oq "$dir/$zip" -d "$dir"
		rm -f "$dir/$zip"
		chmod +x "$dir/zenoh-bridge-ros2dds"
		if [ "$(uname -s)" = Darwin ]; then
			xattr -dr com.apple.quarantine "$dir" 2>/dev/null || true
		fi
	fi
	echo "$dir/zenoh-bridge-ros2dds"
}

mode="${1:-native}"
shift || true

case "$mode" in
up)
	compose up -d sim-bridge
	log "urc-side bridge listening on 127.0.0.1:7447 (domain $ROS_DOMAIN_ID)"
	;;
down)
	compose stop sim-bridge
	;;
native)
	bin="$(native_bin)"
	endpoint="${ZENOH_ENDPOINT:-tcp/127.0.0.1:7447}"
	log "bridging host ROS 2 (domain $ROS_DOMAIN_ID) -> $endpoint"
	exec "$bin" client -e "$endpoint" --no-multicast-scouting "$@"
	;;
docker)
	sim="${SIM_CONTAINER:-simulations}"
	endpoint="${ZENOH_ENDPOINT:-tcp/host.docker.internal:7447}"
	docker inspect "$sim" >/dev/null 2>&1 || die "container '$sim' is not running"
	log "bridging '$sim' ROS 2 (domain $ROS_DOMAIN_ID) -> $endpoint"
	exec docker run --rm -it --name sim-bridge-sim \
		--network "container:$sim" -e ROS_DOMAIN_ID -e ROS_DISTRO \
		"$IMAGE" client -e "$endpoint" --no-multicast-scouting "$@"
	;;
*)
	sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
	exit 1
	;;
esac
