"""Launch localization, Nav2 and the navigation node.

robot_localization's EKFs publish odom -> base_footprint from the ZED's visual odometry and
IMU, and map -> odom from those plus GPS. navsat_transform serves fromLL / toLL in both modes,
once gps_heading_init has found the rover's heading from a few metres of driving.
In simulation, pass use_sim_time:=true, and optionally ground_truth_localization:=true to
relay the simulator's ground-truth odometry instead of running the EKFs.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import IfElseSubstitution, LaunchConfiguration
from launch_ros.actions import Node, SetParameter

# base_link is the CAD origin at the rover's side. base_footprint is the rotation centre,
# midway between the front and rear axles. Position of base_link in base_footprint (m).
BASE_LINK_OFFSET = [0.055, -0.298, 0.0]

GPS_FIX_TOPIC = "/ublox_gps_node/fix"
# With gps_heading_init:=false, navsat_transform takes its earth heading (0 = east) from this
# IMU. The ZED's yaw is relative to where it started, so that only holds in sim, where the
# rover spawns facing east.
HEADING_IMU_TOPIC = "/zed/zed_node/imu/data"
# Nothing publishes this. navsat_transform waits on it until gps_heading_init sets the datum.
NO_HEADING_TOPIC = "/navsat_transform/unused_imu"

# (package, executable, remappings) in lifecycle startup order
NAV2_NODES = [
    ("nav2_controller", "controller_server", [("cmd_vel", "cmd_vel_nav")]),
    ("nav2_smoother", "smoother_server", []),
    ("nav2_planner", "planner_server", []),
    ("nav2_behaviors", "behavior_server", [("cmd_vel", "cmd_vel_nav")]),
    ("nav2_velocity_smoother", "velocity_smoother", [("cmd_vel", "cmd_vel_nav")]),
    ("nav2_collision_monitor", "collision_monitor", []),
    ("nav2_bt_navigator", "bt_navigator", []),
]


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    ground_truth_localization = LaunchConfiguration("ground_truth_localization")
    gps_heading_init = LaunchConfiguration("gps_heading_init")
    params_file = LaunchConfiguration("params_file")
    share_dir = get_package_share_directory("navigation")
    config_dir = os.path.join(share_dir, "config")
    localization_params = os.path.join(config_dir, "localization.yaml")
    # Installed paths, which nav2_params.yaml can't hold
    nav2_overrides = {
        "bt_navigator": {
            "default_nav_to_pose_bt_xml": os.path.join(
                share_dir, "behavior_trees", "navigate_to_pose.xml"
            )
        },
    }

    x, y, z = (str(v) for v in BASE_LINK_OFFSET)
    nav2_nodes = [
        Node(
            package=package,
            executable=executable,
            name=executable,
            parameters=[params_file, nav2_overrides[executable]]
            if executable in nav2_overrides
            else [params_file],
            remappings=remappings,
        )
        for package, executable, remappings in NAV2_NODES
    ]

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use the simulator's /clock topic",
            ),
            DeclareLaunchArgument(
                "ground_truth_localization",
                default_value="false",
                description="Localize from the simulator's ground-truth odometry",
            ),
            DeclareLaunchArgument(
                "gps_heading_init",
                default_value="true",
                description="Find the GPS heading by driving a few metres. false trusts the "
                "IMU's yaw as an earth heading, which only holds in sim",
            ),
            DeclareLaunchArgument(
                "params_file",
                default_value=os.path.join(config_dir, "nav2_params.yaml"),
                description="Nav2 parameters file",
            ),
            SetParameter("use_sim_time", use_sim_time),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="base_footprint_to_base_link",
                arguments=[
                    *("--x", x, "--y", y, "--z", z),
                    *("--frame-id", "base_footprint", "--child-frame-id", "base_link"),
                ],
            ),
            # EKF localization
            Node(
                package="robot_localization",
                executable="ekf_node",
                name="ekf_filter_node_odom",
                parameters=[localization_params],
                condition=UnlessCondition(ground_truth_localization),
            ),
            Node(
                package="robot_localization",
                executable="ekf_node",
                name="ekf_filter_node_map",
                parameters=[localization_params],
                remappings=[("odometry/filtered", "/odometry/global")],
                condition=UnlessCondition(ground_truth_localization),
            ),
            # Ground-truth localization: odom is already earth-fixed, so map == odom
            Node(
                package="navigation",
                executable="ground_truth_odom",
                parameters=[{"base_link_offset": BASE_LINK_OFFSET}],
                condition=IfCondition(ground_truth_localization),
            ),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="map_to_odom",
                arguments=["--frame-id", "map", "--child-frame-id", "odom"],
                condition=IfCondition(ground_truth_localization),
            ),
            # GPS <-> map, taking the robot's pose from whichever source provides map poses
            Node(
                package="robot_localization",
                executable="navsat_transform_node",
                name="navsat_transform",
                parameters=[localization_params],
                remappings=[
                    (
                        "imu",
                        IfElseSubstitution(gps_heading_init, NO_HEADING_TOPIC, HEADING_IMU_TOPIC),
                    ),
                    ("gps/fix", GPS_FIX_TOPIC),
                    (
                        "odometry/filtered",
                        IfElseSubstitution(
                            ground_truth_localization, "/odometry/filtered", "/odometry/global"
                        ),
                    ),
                ],
            ),
            Node(
                package="navigation",
                executable="gps_heading_init",
                remappings=[("gps/fix", GPS_FIX_TOPIC)],
                condition=IfCondition(gps_heading_init),
            ),
            *nav2_nodes,
            Node(
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="lifecycle_manager_navigation",
                parameters=[
                    {
                        "autostart": True,
                        "node_names": [executable for _, executable, _ in NAV2_NODES],
                    }
                ],
            ),
            Node(
                package="navigation",
                executable="gps_navigator",
            ),
            Node(
                package="navigation",
                executable="navigation_node",
            ),
        ]
    )
