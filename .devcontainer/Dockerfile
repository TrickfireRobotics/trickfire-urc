# Base image: minimal Ubuntu. ROS, clang tooling, and Python tooling
# come from the pixi environment defined in /pixi.toml.
FROM ubuntu:24.04

ENV LANG=en_US.UTF-8 \
    TZ=UTC \
    PIXI_HOME=/opt/pixi \
    PATH=/opt/pixi/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    locales \
    openssh-client \
    tzdata \
    && locale-gen en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://pixi.sh/install.sh | \
    env PIXI_HOME=/opt/pixi PIXI_NO_PATH_UPDATE=1 bash

RUN useradd trickfire \
    --shell /bin/bash \
    --create-home \
    --no-log-init \
    -G video \
    && mkdir -p /home/trickfire/trickfire-urc \
    && chown -R trickfire:trickfire /home/trickfire/trickfire-urc

USER trickfire
COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
WORKDIR /home/trickfire/trickfire-urc
