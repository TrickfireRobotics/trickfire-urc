# Base image: Ubuntu 24.04 with ROS2 Jazzy installed
FROM ros:jazzy

# Install dependencies from apt
RUN apt-get update && apt-get install -y \
  git \
  ssh-client \
  ros-jazzy-rosbridge-server \
  clang \
  clang-tidy \
  clang-format \
  pipx \
  python3-pip 

RUN rm -rf /var/lib/apt/lists/*

RUN useradd trickfire \
  --shell /bin/bash \
  --create-home \
  --no-log-init \
  -G video

USER trickfire
RUN pipx install ruff

COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
WORKDIR /home/trickfire
