"""Launch the navigation node with an optional simulation clock."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use the simulator's /clock topic",
            ),
            Node(
                package="navigation",
                executable="navigation_node",
                parameters=[{"use_sim_time": ParameterValue(use_sim_time, value_type=bool)}],
            ),
        ]
    )
