# syntax=docker/dockerfile:1
FROM ros:jazzy-ros-base AS prod
ARG DEBIAN_FRONTEND=noninteractive
ARG L4T_RELEASE=r39.2
ARG CUDA_TOOLKIT_PKG=cuda-toolkit-13-2
ARG ZED_SDK_MAJOR=5
ARG ZED_SDK_MINOR=5
ARG ZED_SDK_PATCH=0
ARG L4T_MAJOR=39
ARG L4T_MINOR=2

ENV LANG=en_US.UTF-8 \
    TZ=UTC \
    PATH=/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility

RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    openssh-client \
    wget \
    && locale-gen en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------
# Nvidia Jetson
# -----------------------------------

RUN wget -q -P /etc/apt/trusted.gpg.d https://repo.download.nvidia.com/jetson/jetson-ota-public.asc && \
    wget -q -P /etc/apt/preferences.d https://repo.download.nvidia.com/jetson/nvidia-repo-pin-600 && \
    echo "deb https://repo.download.nvidia.com/jetson/common ${L4T_RELEASE} main" \
        > /etc/apt/sources.list.d/nvidia-l4t-apt-source.list && \
    apt-get update && apt-get install -y --no-install-recommends "${CUDA_TOOLKIT_PKG}" && \
    rm -rf /var/lib/apt/lists/* \
        /etc/apt/sources.list.d/nvidia-l4t-apt-source.list \
        /etc/apt/preferences.d/nvidia-repo-pin-600 \
        /etc/apt/trusted.gpg.d/jetson-ota-public.asc

# ------------------------------------
# Zed sdk installer
# ------------------------------------

RUN wget -q --no-check-certificate -O /tmp/ZED_SDK_Linux.run \
    "https://download.stereolabs.com/zedsdk/${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}.${ZED_SDK_PATCH}/l4t${L4T_MAJOR}.${L4T_MINOR}/jetsons" \
    && chmod +x /tmp/ZED_SDK_Linux.run \
    && /tmp/ZED_SDK_Linux.run silent skip_tools skip_drivers skip_cuda \
    && rm -rf /tmp/ZED_SDK_Linux.run /usr/local/zed/resources/* \
    && ln -sf /usr/lib/aarch64-linux-gnu/tegra/libv4l2.so.0 /usr/lib/aarch64-linux-gnu/libv4l2.so

# ------------------------------------
# ROS packages used at runtime
# ------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-rosbridge-server \
    ros-jazzy-cv-bridge \
    ros-jazzy-vision-opencv \
    && rm -rf /var/lib/apt/lists/*

RUN useradd trickfire \
    --shell /bin/bash \
    --create-home \
    --no-log-init \
    -G video \
    && mkdir -p /home/trickfire/trickfire-urc \
    && chown -R trickfire:trickfire /home/trickfire/trickfire-urc \
    && echo "trickfire ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/trickfire \
    && chmod 0440 /etc/sudoers.d/trickfire

USER trickfire
COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
WORKDIR /home/trickfire/trickfire-urc


# ------------------------------------
# Dev setup
# ------------------------------------

FROM ros:jazzy-ros-base AS dev

ENV LANG=en_US.UTF-8 \
    TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    clang-format \
    clang-tidy \
    clang-tools \
    clangd \
    cmake \
    gdb \
    git \
    locales \
    openssh-client \
    pipx \
    python3-pip \
    shfmt \
    sudo \
    tzdata \
    && locale-gen en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------
# ROS packages used for development
# ------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-desktop \
    ros-jazzy-rosbridge-server \
    ros-jazzy-cv-bridge \
    ros-jazzy-vision-opencv \
    ros-jazzy-pinocchio \
    ros-jazzy-coal \
    && rm -rf /var/lib/apt/lists/*

RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install ruff==0.15.14 \
    && chmod -R a+rX /opt/pipx

RUN useradd trickfire \
    --shell /bin/bash \
    --create-home \
    --no-log-init \
    -G video \
    && mkdir -p /home/trickfire/trickfire-urc \
    && chown -R trickfire:trickfire /home/trickfire/trickfire-urc \
    && echo "trickfire ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/trickfire \
    && chmod 0440 /etc/sudoers.d/trickfire

USER trickfire
COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
WORKDIR /home/trickfire/trickfire-urc
