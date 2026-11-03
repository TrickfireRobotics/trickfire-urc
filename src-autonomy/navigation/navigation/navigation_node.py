"""Mission state machine: takes navigation goals and runs them through the navigation actions."""

import math
from dataclasses import dataclass
from enum import Enum

import rclpy
from action_msgs.msg import GoalStatus
from geographic_msgs.msg import GeoPoint
from geometry_msgs.msg import PoseStamped
from navigation_interfaces.action import NavigateToGPS, NavigateToTarget
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix

SHARED_ERRORS = ("NONE", "NAV2_REJECTED", "NAV2_FAILED", "GOAL_BLOCKED", "TIMED_OUT")


def _error_names(action_type, *names):
    return {getattr(action_type.Result, name): name for name in (*SHARED_ERRORS, *names)}


class MissionState(Enum):
    """Enum class for mission state"""

    IDLE = 0
    NAVIGATING_GPS = 1
    NAVIGATING_TARGET = 2
    COMPLETE = 3
    FAILED = 4


@dataclass(frozen=True)
class NavAction:
    """A navigation action server as the state machine drives it"""

    client: ActionClient
    name: str
    state: MissionState  # while a goal of its runs
    error_names: dict  # result error code -> name


class NavigationNode(Node):
    """Node to sequence mission goals through the navigation action servers"""

    def __init__(self):
        super().__init__("navigation_node")
        self.state = MissionState.IDLE
        # The latest goal: its action, send request, and handle once accepted. Responses for
        # anything older belong to goals the servers have already replaced, so they're ignored.
        # _request is None once the goal has ended.
        self._action = None
        self._request = None
        self._goal_handle = None
        # A goal held back until the one in progress, on the other server, has ended:
        # (action, goal, label)
        self._queued = None

        self._gps = NavAction(
            ActionClient(self, NavigateToGPS, "navigate_to_gps"),
            "navigate_to_gps",
            MissionState.NAVIGATING_GPS,
            _error_names(NavigateToGPS, "NO_GPS_FIX", "CONVERSION_FAILED"),
        )
        self._target = NavAction(
            ActionClient(self, NavigateToTarget, "navigate_to_target"),
            "navigate_to_target",
            MissionState.NAVIGATING_TARGET,
            _error_names(NavigateToTarget, "TRANSFORM_FAILED"),
        )
        self.create_subscription(NavSatFix, "/goal/gnss", self._on_gnss_goal, 10)
        self.create_subscription(PoseStamped, "/goal/pose", self._on_pose_goal, 10)

    def _set_state(self, state: MissionState):
        if state != self.state:
            self.get_logger().info(f"{self.state.name} -> {state.name}")
            self.state = state

    def _on_gnss_goal(self, fix: NavSatFix):
        if not (math.isfinite(fix.latitude) and math.isfinite(fix.longitude)):
            self.get_logger().error(
                f"Ignoring GNSS goal at invalid position ({fix.latitude}, {fix.longitude})"
            )
            return
        self.get_logger().info(f"GNSS goal ({fix.latitude:.7f}, {fix.longitude:.7f})")
        goal = NavigateToGPS.Goal(
            target=GeoPoint(latitude=fix.latitude, longitude=fix.longitude, altitude=fix.altitude)
        )
        self._send(self._gps, goal, "GNSS goal")

    def _on_pose_goal(self, pose: PoseStamped):
        p = pose.pose.position
        if not all(math.isfinite(v) for v in (p.x, p.y, p.z)) or not pose.header.frame_id:
            self.get_logger().error(
                f"Ignoring pose goal ({p.x}, {p.y}, {p.z}) in frame '{pose.header.frame_id}'"
            )
            return
        self.get_logger().info(f"Pose goal ({p.x:.2f}, {p.y:.2f}) in '{pose.header.frame_id}'")
        goal = NavigateToTarget.Goal(target=pose)
        self._send(self._target, goal, "Pose goal")

    def _send(self, action, goal, label):
        """Run goal on action, replacing the goal in progress.

        A server replaces its own goal in progress. One on the other server would keep driving
        Nav2 alongside the new goal, so that one is canceled first and this goal waits for it.
        """
        if self._request is not None and self._action is not action:
            if self._action.client.server_is_ready():
                self.get_logger().info(f"{label} waits for the {self._action.name} goal to end")
                self._queued = (action, goal, label)
                if self._goal_handle is not None:
                    self._cancel(self._goal_handle)
                # Else it's canceled once accepted, in _on_goal_response
                return
            # Its server is gone, and so is its goal
            self.get_logger().warning(f"The {self._action.name} action server has gone away")
            self._request = None
        self._queued = None
        self._goal_handle = None
        if not action.client.server_is_ready():
            # Any goal of its own in progress died with it
            self.get_logger().error(f"The {action.name} action server isn't available")
            self._request = None
            self._set_state(MissionState.FAILED)
            return
        self._action = action
        self._request = action.client.send_goal_async(goal, feedback_callback=self._on_feedback)
        self._request.add_done_callback(lambda request: self._on_goal_response(request, label))
        self._set_state(action.state)

    def _cancel(self, goal_handle):
        """Cancel goal_handle so the queued goal can run once its result arrives"""
        goal_handle.cancel_goal_async().add_done_callback(
            lambda future: self._on_cancel_response(goal_handle, future)
        )

    def _on_cancel_response(self, goal_handle, future):
        if goal_handle is not self._goal_handle or future.result().goals_canceling:
            return
        # The server doesn't know the goal, so it was restarted since: no result is coming.
        # (Or the goal has just ended, and the result that's coming will be ignored as stale.)
        self.get_logger().warning(f"The {self._action.name} server has forgotten the goal")
        self._goal_handle = None
        self._request = None
        self._send_queued()

    def _send_queued(self):
        if self._queued is not None:
            self._send(*self._queued)

    def _on_goal_response(self, request, label):
        if request is not self._request:
            return
        goal_handle = request.result()
        if not goal_handle.accepted:
            self.get_logger().error(f"{label} rejected by its action server")
            self._request = None
            self._set_state(MissionState.FAILED)
            self._send_queued()
            return
        self._goal_handle = goal_handle
        if self._queued is not None:
            self._cancel(goal_handle)
        goal_handle.get_result_async().add_done_callback(
            lambda future: self._on_result(goal_handle, future, label)
        )

    def _on_feedback(self, msg):
        self.get_logger().info(
            f"{msg.feedback.distance_remaining:.1f} m to go", throttle_duration_sec=5.0
        )

    def _on_result(self, goal_handle, future, label):
        if goal_handle is not self._goal_handle:
            return
        self._goal_handle = None
        self._request = None
        response = future.result()
        if response.status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"{label} reached")
            self._set_state(MissionState.COMPLETE)
        elif response.status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info(f"{label} canceled")
            self._set_state(MissionState.IDLE)
        else:
            result = response.result
            error = self._action.error_names.get(result.error_code, str(result.error_code))
            self.get_logger().error(f"{label} failed ({error}): {result.error_msg}")
            self._set_state(MissionState.FAILED)
        self._send_queued()


def main(args=None):
    rclpy.init(args=args)
    node = NavigationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
