from launch import LaunchDescription
from launch_ros_actions import Node

ar_tag_detection_node = Node(
        package="ar_tag_detection", executable="ar_tag_detection", name="ar_tag_detection"
    )

def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
           ar_tag_detection_node
        ]
    )
