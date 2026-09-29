"""Accept rover pose goals and run them through Nav2's action interface."""

import threading
from enum import Enum

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import NavSatFix


class MissionState(Enum):
    """Enum class for mission state"""

    IDLE = 0
    NAVIGATING = 1
    COMPLETE = 2


class NavigationNode(Node):
    """Node to handle navigation dispatch and goal handling"""

    def __init__(self):
        super().__init__("navigation_node")
        self.declare_parameter("ground_truth_localization", False)
        self.ground_truth_localization = self.get_parameter("ground_truth_localization").value
        self.state = MissionState.IDLE
        self._pending_goal = None
        self._goal_lock = threading.Lock()
        self._goal_event = threading.Event()
        self._stop_event = threading.Event()
        self.latest_gps_fix = None

        self.create_subscription(PoseStamped, "/goal/pose", self._on_goal, 10)
        self.create_subscription(NavSatFix, "/gps/fix", self._on_gps_fix, 10)
        self.create_subscription(NavSatFix, "/goal/gnss", self._on_gnss_goal, 10)
        if not self.ground_truth_localization:
            self.create_subscription(PoseStamped, "/pose/current", self._on_current_pose, 10)

        self.navigator = BasicNavigator()
        if self.get_parameter("use_sim_time").value:
            self.navigator.set_parameters([Parameter("use_sim_time", value=True)])
        self._initial_pose_sent = False
        self._worker = threading.Thread(target=self._run, name="navigation_worker", daemon=True)
        self._worker.start()

    def _on_current_pose(self, pose: PoseStamped):
        if not self._initial_pose_sent:
            self.navigator.setInitialPose(pose)
            self._initial_pose_sent = True

    def _on_goal(self, pose: PoseStamped):
        expected_frame = "odom" if self.ground_truth_localization else "map"
        if pose.header.frame_id != expected_frame:
            self.get_logger().error(
                f"Goal frame must be '{expected_frame}', received '{pose.header.frame_id}'"
            )
            return
        with self._goal_lock:
            self._pending_goal = pose
        self._goal_event.set()

    def _on_gps_fix(self, fix: NavSatFix):
        self.latest_gps_fix = fix

    def _on_gnss_goal(self, _fix: NavSatFix):
        self.get_logger().warning(
            "GNSS goals need a geographic-to-local transform; send /goal/pose for now"
        )

    def _take_goal(self):
        with self._goal_lock:
            goal = self._pending_goal
            self._pending_goal = None
            self._goal_event.clear()
            return goal

    def _run(self):
        self.get_logger().info("Waiting for Nav2 to activate")
        if self.ground_truth_localization:
            # The simulator publishes odom -> base_link directly. No AMCL or initial pose.
            self.navigator.waitUntilNav2Active(localizer="robot_localization")
        else:
            self.navigator.waitUntilNav2Active()
        self.get_logger().info("Ready for /goal/pose")

        while not self._stop_event.is_set() and rclpy.ok():
            if not self._goal_event.wait(timeout=0.2):
                continue
            goal = self._take_goal()
            if goal is None:
                continue
            self.state = MissionState.NAVIGATING
            if not self.navigator.goToPose(goal):
                self.state = MissionState.IDLE
                self.get_logger().error("Nav2 rejected the navigation goal")
                continue
            while not self._stop_event.is_set() and rclpy.ok():
                if self._goal_event.is_set():
                    self.navigator.cancelTask()
                    break
                if self.navigator.isTaskComplete():
                    result = self.navigator.getResult()
                    if result == TaskResult.SUCCEEDED:
                        self.state = MissionState.COMPLETE
                        self.get_logger().info("Navigation goal reached")
                    else:
                        self.state = MissionState.IDLE
                        self.get_logger().warning(f"Navigation ended: {result.name}")
                    break
                self._stop_event.wait(0.1)

    def stop(self):
        self._stop_event.set()
        self._goal_event.set()


def main(args=None):
    rclpy.init(args=args)
    node = NavigationNode()
    executor = SingleThreadedExecutor()
    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
