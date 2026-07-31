#!/usr/bin/env bash
set -euo pipefail

ZED_SDK_VERSION="4.2"

if [[ "$(uname -m)" == "aarch64" ]]; then
    ZED_URL="https://download.stereolabs.com/zedsdk/${ZED_SDK_VERSION}/l4t36.3/jetsons"
else
    ZED_URL="https://download.stereolabs.com/zedsdk/${ZED_SDK_VERSION}/cu121/ubuntu22"
fi

if /usr/local/zed/tools/ZED_Diagnostic 2>/dev/null | grep -q "ZED SDK v${ZED_SDK_VERSION}"; then
    echo "ZED SDK ${ZED_SDK_VERSION} already installed."
else
    echo "Installing ZED SDK ${ZED_SDK_VERSION}..."
    TMP=$(mktemp --suffix=.run)
    wget -q --show-progress -O "$TMP" "$ZED_URL"
    chmod +x "$TMP"
    sudo "$TMP" -- silent skip_od_module skip_python
    rm "$TMP"
fi
