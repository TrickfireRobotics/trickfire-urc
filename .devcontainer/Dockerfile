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
  python3-pip \
  apt-get install --no-install-recommends -y locales && \
  locale-gen en_US en_US.UTF-8 && \
  update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 &&

RUN rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8

RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime && \
    echo "${TZ}" > /etc/timezone

RUN useradd trickfire \
  --shell /bin/bash \
  --create-home \
  --no-log-init \
  -G video

USER trickfire
RUN pipx install ruff

COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
WORKDIR /home/trickfire
