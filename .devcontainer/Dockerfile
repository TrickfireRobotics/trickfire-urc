# syntax=docker/dockerfile:1
# Build from the repository root with --target dev or --target prod.
# Dev is the default target and does not build or pull the Jetson stages.
ARG ROVER_BASE_IMAGE=stereolabs/zed:5.4.1-devel-l4t-r39.2@sha256:0a9e063d6c8a128115ec8e929c9f9158f6d0c3d0d5f0d740c99d0405190950de

# Share the dependency list, not installed binaries: each target has its own base
# and may use a different CPU architecture. Install packages inside each image.
FROM scratch AS common
COPY <<'PACKAGES' /common-packages.txt
build-essential
git
python3-colcon-common-extensions
python3-numpy
python3-opencv
python3-pip
python3-rosdep
ros-jazzy-coal
ros-jazzy-cv-bridge
ros-jazzy-pinocchio
ros-jazzy-ros-base
ros-jazzy-rosbridge-server
PACKAGES

# prod: Jetson AGX Orin / JetPack 7.2 (L4T 39.2, Ubuntu 24.04).
# The base includes CUDA and ZED SDK 5.4.1; the host provides kernel drivers.
# Workspaces remain bind-mounted until the rover application has a launch target.
FROM ${ROVER_BASE_IMAGE} AS prod
ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG ROS_APT_SOURCE_VERSION=1.2.0
ARG ZED_WRAPPER_TAG=v5.4.1

RUN test "${TARGETARCH}" = arm64 || { \
  echo "ERROR: Build prod with --platform linux/arm64 for the Jetson." >&2; exit 1; \
  }
# ROS Jazzy apt packages require Noble; the wrapper also needs the CUDA compiler.
RUN . /etc/os-release && \
  test "${ID}:${VERSION_ID}" = "ubuntu:24.04" || { \
  echo "ERROR: ROVER_BASE_IMAGE must use Ubuntu 24.04 for ROS Jazzy apt packages." >&2; exit 1; \
  }
RUN test -x /usr/local/cuda/bin/nvcc || { \
  echo "ERROR: ROVER_BASE_IMAGE must include the CUDA development toolkit at /usr/local/cuda." >&2; exit 1; \
  }
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,video

# Add the ROS repository to the hardware base.
RUN apt-get update && \
  apt-get install -y --no-install-recommends ca-certificates curl && \
  curl -fsSL -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${VERSION_CODENAME})_all.deb" && \
  apt-get install -y --no-install-recommends /tmp/ros2-apt-source.deb && \
  rm -f /tmp/ros2-apt-source.deb && \
  rm -rf /var/lib/apt/lists/*

# The mounted list is build input only; xargs appends it to the target's packages.
RUN --mount=type=bind,from=common,source=/common-packages.txt,target=/tmp/common-packages.txt \
  apt-get update && \
  xargs apt-get install -y --no-install-recommends \
  cmake \
  libgomp1 \
  libpng-dev \
  libusb-1.0-0-dev \
  < /tmp/common-packages.txt && \
  rm -rf /var/lib/apt/lists/*

# Verify the SDK supplied by the base before building the ROS wrapper.
RUN test -f /usr/local/zed/include/sl/Camera.hpp && \
  test -f /usr/local/zed/zed-config.cmake && \
  echo /usr/local/zed/lib > /etc/ld.so.conf.d/zed.conf && \
  ldconfig

# Link with CUDA stubs during build; the host supplies driver libraries at runtime.
RUN git clone --branch "${ZED_WRAPPER_TAG}" --depth 1 --recurse-submodules \
  https://github.com/stereolabs/zed-ros2-wrapper.git \
  /opt/zed_ws/src/zed-ros2-wrapper && \
  apt-get update && \
  if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
  rosdep update && \
  rosdep install --from-paths /opt/zed_ws/src --ignore-src -y --rosdistro jazzy && \
  . /opt/ros/jazzy/setup.sh && \
  cd /opt/zed_ws && \
  colcon build --parallel-workers "$(nproc)" \
  --cmake-args -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_LIBRARY_PATH=/usr/local/cuda/lib64/stubs \
  -DCMAKE_CXX_FLAGS="-Wl,--allow-shlib-undefined" && \
  rm -rf /opt/zed_ws/build /opt/zed_ws/log /var/lib/apt/lists/*

COPY --chmod=755 <<'ENTRYPOINT' /usr/local/bin/rover-entrypoint.sh
#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source /opt/zed_ws/install/setup.bash
for ws in /trickfire-urc/src-autonomy /trickfire-urc/src-platform; do
    if [ -f "${ws}/install/setup.bash" ]; then
        source "${ws}/install/setup.bash"
    fi
done
exec "$@"
ENTRYPOINT
RUN sed -i 's/\r$//' /usr/local/bin/rover-entrypoint.sh
WORKDIR /trickfire-urc
ENTRYPOINT ["/usr/local/bin/rover-entrypoint.sh"]
CMD ["bash"]

# dev: portable ROS environment for linux/amd64 and linux/arm64.
# This stage depends only on common and ros:jazzy, not on prod.
FROM ros:jazzy AS dev
ARG DEBIAN_FRONTEND=noninteractive

# Keep compiled Python dependencies on Ubuntu/ROS packages for ABI compatibility.
RUN --mount=type=bind,from=common,source=/common-packages.txt,target=/tmp/common-packages.txt \
  apt-get update && \
  xargs apt-get install -y --no-install-recommends \
  bash-completion \
  clang-format \
  clang-tidy \
  clang-tools \
  clangd \
  gdb \
  openssh-client \
  python3-pytest \
  ros-jazzy-desktop \
  shfmt \
  < /tmp/common-packages.txt && \
  rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir --break-system-packages ruff==0.16.5

# Remove the stock Ubuntu user before creating the development user.
ARG UID=1000
ARG GID=1000
RUN if id ubuntu >/dev/null 2>&1; then userdel --remove ubuntu; fi && \
  if getent group ubuntu >/dev/null; then groupdel ubuntu; fi && \
  groupadd --gid "${GID}" trickfire && \
  useradd --uid "${UID}" --gid trickfire --shell /bin/bash \
  --create-home --no-log-init -G video trickfire && \
  mkdir -p /home/trickfire/trickfire-urc && \
  chown trickfire:trickfire /home/trickfire/trickfire-urc

COPY --chown=trickfire:trickfire .devcontainer/trickfire.bashrc /home/trickfire/.bashrc
COPY --chmod=755 .devcontainer/dev-smoke-test.sh /usr/local/bin/dev-smoke-test

USER trickfire
WORKDIR /home/trickfire/trickfire-urc
CMD ["bash"]
