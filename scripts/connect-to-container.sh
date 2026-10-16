#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

exec docker compose -f .devcontainer/docker-compose.yml exec robot /bin/bash
