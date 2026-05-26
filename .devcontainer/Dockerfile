# Base image: Ubuntu 24.04 with ROS2 Jazzy installed
FROM ros:jazzy

ENV LANG=en_US.UTF-8
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    git \
    ssh-client \
    ros-jazzy-rosbridge-server \
    clang \
    clang-tidy \
    clang-format \
    pipx \
    python3-pip \
    locales \
    tzdata \
    && locale-gen en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

RUN useradd trickfire \
    --shell /bin/bash \
    --create-home \
    --no-log-init \
    -G video \
    && mkdir -p /home/trickfire/trickfire-urc \
    && chown -R trickfire:trickfire /home/trickfire/trickfire-urc

USER trickfire
RUN pipx install ruff

COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
WORKDIR /home/trickfire/trickfire-urc
