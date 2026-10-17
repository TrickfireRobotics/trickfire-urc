#!/usr/bin/env bash
# Usage: ./scripts/container.sh [-a] [-n] [-c]
#   -a  Attach only, without building or starting the container
#   -n  Rebuild the Docker image without using the build cache
#   -c  Force recreate the container, even if it already exists

set -eo pipefail
cd "$(dirname "$0")/.."

readonly log_prefix="TRICKFIRE DOCKER"
readonly compose_file=".devcontainer/docker-compose.yml"
readonly service="robot"

readonly blue='\033[0;34m'
readonly green='\033[0;32m'
readonly reset='\033[0m'

log_info() { echo -e "${blue}$(tput bold)[${log_prefix}] $1${reset}"; }
log_success() { echo -e "${green}$(tput bold)[${log_prefix}] $1${reset}"; }
compose() { docker compose -f "$compose_file" "$@"; }

attach_only=false
no_cache=false
force_recreate=false

while getopts 'anc' flag; do
    case "$flag" in
    a) attach_only=true ;;
    n) no_cache=true ;;
    c) force_recreate=true ;;
    *)
        echo "Usage: $0 [-a] [-n] [-c]" >&2
        exit 1
        ;;
    esac
done

if [[ $attach_only == false ]]; then
    log_info "Building '${service}' image"
    if [[ $no_cache == true ]]; then
        compose build --no-cache "$service"
    else
        compose build "$service"
    fi

    log_info "Starting '${service}' container"
    if [[ $force_recreate == true ]]; then
        compose up -d --force-recreate "$service"
    else
        compose up -d "$service"
    fi
    log_success "Launch of '${service}' succeeded"
fi

log_info "Connecting to '${service}' container"
exec docker compose -f "$compose_file" exec "$service" /bin/bash
