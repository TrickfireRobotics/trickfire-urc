import os

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# ------------------------------- Process Nodes ------------------------------ #

heartbeat_node = Node(package="heartbeat", executable="heartbeat", name="heartbeat_node")

ar_tag_detection_node = Node(
    package="ar_tag_detection", executable="ar_tag_detection", name="ar_tag_detection"
)

object_detection_node = Node(
    package="object_detection",
    executable="object_detection_node",
    name="object_detection",
    output="screen",
    parameters=[
        {
            "image_topic": [
                "/",
                LaunchConfiguration("zed_camera_name"),
                "/zed_node/rgb/color/rect/image",
            ],
        }
    ],
)

# ----------------------------- Launch Arguments ----------------------------- #

launch_arguments = [
    DeclareLaunchArgument(
        "enable_zed",
        default_value="true",
        description="Start the ZED camera driver",
    ),
    DeclareLaunchArgument(
        "zed_camera_model",
        default_value="zed2i",
        description="ZED camera model passed to zed_wrapper",
    ),
    DeclareLaunchArgument(
        "zed_camera_name",
        default_value="zed",
        description="Name used for the ZED namespace and TF frames",
    ),
]

# ---------------------------- Launch Description ---------------------------- #


def generate_launch_description() -> LaunchDescription:
    launch_description = LaunchDescription(
        [
            # launch arguments
            *launch_arguments,
            #
            # modules
            heartbeat_node,
            object_detection_node,
            ar_tag_detection_node,
            #
            # includes
            _zed_camera(),
        ]
    )

    return launch_description


# ---------------------------------------------------------------------------- #
#                                    Helpers                                   #
# ---------------------------------------------------------------------------- #


# zed_wrapper requires ZED & CUDA skip when unavailable
def _zed_camera() -> LogInfo | IncludeLaunchDescription:
    try:
        zed_share = get_package_share_directory("zed_wrapper")
    except PackageNotFoundError:
        return LogInfo(msg="zed_wrapper is not installed, skipping the ZED camera.")

    overrides = os.path.join(
        get_package_share_directory("rover_launch"), "config", "zed_overrides.yaml"
    )
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(zed_share, "launch", "zed_camera.launch.py")),
        launch_arguments={
            "camera_model": LaunchConfiguration("zed_camera_model"),
            "camera_name": LaunchConfiguration("zed_camera_name"),
            "ros_params_override_path": overrides,
        }.items(),
        condition=IfCondition(LaunchConfiguration("enable_zed")),
    )
