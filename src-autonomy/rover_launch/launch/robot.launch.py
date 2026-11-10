from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="object_detection",
                executable="object_detection_node",
                name="object_detection",
                output="screen",
            ),
        ]
    )
