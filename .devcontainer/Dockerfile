# syntax=docker/dockerfile:1
FROM ros:jazzy-ros-base AS base
ARG DEBIAN_FRONTEND=noninteractive

ENV LANG=en_US.UTF-8 \
    TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    locales \
    openssh-client \
    ros-jazzy-cv-bridge \
    ros-jazzy-rosbridge-server \
    ros-jazzy-vision-opencv \
    wget \
    && locale-gen en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

RUN usermod --login trickfire --home /home/trickfire --move-home ubuntu \
    && groupmod --new-name trickfire ubuntu \
    && usermod -aG video trickfire \
    && mkdir -p /home/trickfire/trickfire-urc \
    && chown -R trickfire:trickfire /home/trickfire/trickfire-urc \
    && echo "trickfire ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/trickfire \
    && chmod 0440 /etc/sudoers.d/trickfire

COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
WORKDIR /home/trickfire/trickfire-urc

# ------------------------------------
# Rover runtime
# ------------------------------------

FROM base AS rover
ARG L4T_RELEASE=r39.2
ARG CUDA_TOOLKIT_PKG=cuda-toolkit-13-2
ARG ZED_SDK_MAJOR=5
ARG ZED_SDK_MINOR=5
ARG ZED_SDK_PATCH=0
ARG L4T_MAJOR=39
ARG L4T_MINOR=2
ARG ZED_ROS2_WRAPPER_REF=v5.5.0
ARG ZED_ROS2_INTERFACES_REF=5.5.0

ENV PATH=/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,video,utility \
    ZED_DIR=/usr/local/zed

RUN wget -q -P /etc/apt/trusted.gpg.d https://repo.download.nvidia.com/jetson/jetson-ota-public.asc && \
    wget -q -P /etc/apt/preferences.d https://repo.download.nvidia.com/jetson/nvidia-repo-pin-600 && \
    echo "deb https://repo.download.nvidia.com/jetson/common ${L4T_RELEASE} main" \
    > /etc/apt/sources.list.d/nvidia-l4t-apt-source.list && \
    apt-get update && apt-get install -y --no-install-recommends "${CUDA_TOOLKIT_PKG}" zstd && \
    rm -rf /var/lib/apt/lists/* \
    /etc/apt/sources.list.d/nvidia-l4t-apt-source.list \
    /etc/apt/preferences.d/nvidia-repo-pin-600 \
    /etc/apt/trusted.gpg.d/jetson-ota-public.asc

RUN wget -q --no-check-certificate -O /tmp/ZED_SDK_Linux.run \
    "https://download.stereolabs.com/zedsdk/${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}.${ZED_SDK_PATCH}/l4t${L4T_MAJOR}.${L4T_MINOR}/jetsons" \
    && chmod +x /tmp/ZED_SDK_Linux.run \
    && /tmp/ZED_SDK_Linux.run silent skip_tools skip_drivers skip_cuda \
    && rm -rf /tmp/ZED_SDK_Linux.run /usr/local/zed/resources/* \
    && ln -sf /usr/lib/aarch64-linux-gnu/tegra/libv4l2.so.0 /usr/lib/aarch64-linux-gnu/libv4l2.so

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    python3-rosdep \
    nlohmann-json3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi \
    && rosdep update \
    && mkdir -p /opt/zed-ros2-wrapper/src \
    && git clone --depth 1 --branch "${ZED_ROS2_WRAPPER_REF}" \
        https://github.com/stereolabs/zed-ros2-wrapper.git \
        /opt/zed-ros2-wrapper/src/zed-ros2-wrapper \
    && git clone --depth 1 --branch "${ZED_ROS2_INTERFACES_REF}" \
        https://github.com/stereolabs/zed-ros2-interfaces.git \
        /opt/zed-ros2-wrapper/src/zed-ros2-interfaces \
    && . /opt/ros/jazzy/setup.sh \
    && apt-get update \
    && rosdep install --from-paths /opt/zed-ros2-wrapper/src --ignore-src -r -y \
    && rm -rf /var/lib/apt/lists/* \
    && cd /opt/zed-ros2-wrapper \
    && colcon build --symlink-install --packages-skip zed_debug \
    --cmake-args -DCMAKE_BUILD_TYPE=Release -DZED_DIR=/usr/local/zed

ENV CMAKE_PREFIX_PATH=/usr/local/zed:/opt/zed-ros2-wrapper/install/zed_msgs:/opt/zed-ros2-wrapper/install/zed_components:/opt/zed-ros2-wrapper/install/zed_wrapper \
    LD_LIBRARY_PATH=/usr/local/zed/lib:${LD_LIBRARY_PATH}

RUN chmod -R a+rX /usr/local /opt/zed-ros2-wrapper \
    && mkdir -p /home/trickfire/.colcon \
    && printf 'build:\n  packages-skip:\n    - zed_debug\n' > /home/trickfire/.colcon/defaults.yaml \
    && chown -R trickfire:trickfire /usr/local/zed/settings /home/trickfire/.colcon \
    && echo 'export ZED_DIR=/usr/local/zed' >> /home/trickfire/.bashrc \
    && echo 'export CMAKE_PREFIX_PATH=/usr/local/zed:${CMAKE_PREFIX_PATH}' >> /home/trickfire/.bashrc \
    && echo 'export LD_LIBRARY_PATH=/usr/local/zed/lib:${LD_LIBRARY_PATH}' >> /home/trickfire/.bashrc \
    && echo 'if [ -f /opt/zed-ros2-wrapper/install/setup.bash ]; then source /opt/zed-ros2-wrapper/install/setup.bash; fi' >> /home/trickfire/.bashrc

USER trickfire

# ------------------------------------
# Devcontainer runtime
# ------------------------------------

FROM rover AS dev

# Switch back to root to install dev tools
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    clang-format \
    clang-tidy \
    clang-tools \
    clangd \
    cmake \
    gdb \
    pipx \
    python3-numpy \
    python3-opencv \
    python3-pip \
    shfmt \
    sudo \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# ROS packages used for development
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-coal \
    ros-jazzy-desktop \
    ros-jazzy-pinocchio \
    && rm -rf /var/lib/apt/lists/*

RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install ruff==0.15.14 \
    && PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install pre-commit \
    && chmod -R a+rX /opt/pipx

# Switch back to the non-root user
USER trickfire
