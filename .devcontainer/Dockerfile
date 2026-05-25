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
  python3-pip 

RUN pip3 install ruff --break-system-packages
RUN rm -rf /var/lib/apt/lists/*

RUN useradd trickfire \
  --shell /bin/bash \
  --create-home \
  --no-log-init \
  -G video

COPY .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
