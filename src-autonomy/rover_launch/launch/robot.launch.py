import os

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    launch_description = LaunchDescription(
        [
            DeclareLaunchArgument(
                "enable_zed",
                default_value="true",
                description="Start the ZED camera driver.",
            ),
            DeclareLaunchArgument(
                "zed_camera_model",
                default_value="zed2i",
                description="ZED camera model passed to zed_wrapper (e.g. zed2i, zedx, zedm).",
            ),
            DeclareLaunchArgument(
                "zed_camera_name",
                default_value="zed",
                description="Name used for the ZED namespace and TF frames.",
            ),
        ]
    )

    # zed_wrapper is only built into the rover image (it needs the ZED SDK and CUDA),
    # so skip the camera instead of failing the whole launch in the dev container.
    try:
        zed_wrapper_share = get_package_share_directory("zed_wrapper")
    except PackageNotFoundError:
        launch_description.add_action(
            LogInfo(msg="zed_wrapper is not installed, skipping the ZED camera.")
        )
        return launch_description

    launch_description.add_action(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(zed_wrapper_share, "launch", "zed_camera.launch.py")
            ),
            launch_arguments={
                "camera_model": LaunchConfiguration("zed_camera_model"),
                "camera_name": LaunchConfiguration("zed_camera_name"),
            }.items(),
            condition=IfCondition(LaunchConfiguration("enable_zed")),
        )
    )

    return launch_description
