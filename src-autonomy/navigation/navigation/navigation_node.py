"""
This node is the main driver for the autonomous navigation loop. It contains a finite state
machine for the navigation loop. The possible states for the rover are idle, navigating, and
finished. When the rover is finished, the lights need to be actived to signal the goal has been
reached
"""

import threading
import time
from enum import Enum

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator
from rclpy import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import NavSatFix


class MissionState(Enum):
    # TODO: Expand to searching for AR tag target state
    IDLE = 0
    NAVIGATING = 1
    COMPLETE = 2


class NavigationNode(Node):
    def __init__(self):
        self.cb_group = ReentrantCallbackGroup()

        self.state: MissionState = MissionState.IDLE

        self.current_pose: PoseStamped | None = None
        self.goal_pose: NavSatFix | None = None

        self.is_first = True

        # ====================== Subscribers ======================
        self.current_pose_subscription = self.create_subscription(
            PoseStamped,
            "/pose/current",
            self.current_pose_callback,
            10,
            callback_group=self.cb_group,
        )

        self.gnss_subscription = self.create_subscription(
            NavSatFix,
            "/goal/gnss",
            self.goal_pose_callback,
            10,
            callback_group=self.cb_group,
        )

        self.navigator: BasicNavigator = BasicNavigator()

        self.logic_thread = threading.Thread(target=self.run_navigation_logic)
        self.logic_thread.start()

    def current_pose_callback(self, msg):
        self.get_logger().info(f"Current pose: {msg.data}")
        self.current_pose = msg.data
        if self.is_first:
            # is first message through this callback - use for init pose
            self.set_start_point(msg.data)
            self.is_first = False

    def goal_pose_callback(self, msg):
        self.get_logger().info(f"Goal message received: {msg.data}")
        self.goal_pose = msg.data

    def set_start_point(self, pose: PoseStamped):
        self.navigator.setInitialPose(pose)

    def set_goal_point(self, pose: PoseStamped):
        self.navigator.goToPose(pose)

    # Entry point
    def run_navigation_logic(self) -> None:
        self.get_logger().info("Waiting for Nav2 to start...")
        self.navigator.waitUntilNav2Active()
        self.get_logger().info("Nav2 is fully active! Proceeding with code.")
        self.run_state_machine()

    # State machine
    def run_state_machine(self):
        if self.state == 0:
            self.get_logger().info("Currently idling...")
        elif self.state == 1:
            while not self.navigator.isTaskComplete():
                time.sleep(0.1)
                self.get_logger().info(f"Navigation state: {self.state}")
                self.get_logger().info(f"Navigation Feedback: {self.navigator.getFeedback()}")
            return self.navigator.getResult()
        else:
            self.get_logger().info("Finished task")

    def idle(self) -> None:
        self.get_logger().info("Navigation: Idle")
        self.navigator.cancelTask()

    def navigate(self, pose: PoseStamped):
        self.get_logger().info(f"Navigating to pose: {pose}")
        self.navigator.goToPose(pose)

    def arrived(self):
        self.get_logger().info("Navigation: Arrived")

    # TODO: Add method/state to search for AR tag in the vicinity, consider slow 360 degree spin to
    # find it


def main(args=None):
    rclpy.init(args=args)
    node = NavigationNode()

    # Must use MultiThreadedExecutor because of basic navigator
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info("Navigation: Keyboard interruption")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
