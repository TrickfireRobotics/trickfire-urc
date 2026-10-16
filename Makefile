.DEFAULT_GOAL := help

COMPOSE_FILE := .devcontainer/docker-compose.yml
SERVICE := robot
LAUNCH_PACKAGE ?= trickfire_urc_launch
LAUNCH_FILE ?= robot.launch.py

.PHONY: help build clean launch container connect format hooks

help:
	@printf '%s\n' \
		'Usage: make <target>' \
		'' \
		'Targets:' \
		'  container  Build, start, and attach to the development container' \
		'             Set CONTAINER_ARGS="-n -c" for a cacheless rebuild and recreation' \
		'  build      Build packages in src-platform and src-autonomy' \
		'  launch     Launch $${LAUNCH_PACKAGE} $${LAUNCH_FILE}' \
		'  connect    Attach to the running development container' \
		'  clean      Remove colcon build artifacts' \
		'  format     Format supported source files' \
		'  hooks      Install git hooks'

build:
	./scripts/build.sh

clean:
	rm -rf build install log

launch:
	./scripts/launch.sh

container:
	./scripts/container-launch.sh $(CONTAINER_ARGS)

connect:
	./scripts/connect-to-container.sh

format:
	ruff format src-autonomy src-platform
	ruff check --fix src-autonomy src-platform
	shfmt -i 4 -s -w scripts/ .devcontainer/

hooks:
	pre-commit install
