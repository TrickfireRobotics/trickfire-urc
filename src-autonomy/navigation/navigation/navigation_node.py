"""Mission state machine: takes GNSS goals and runs them through the navigation actions."""

import math
from enum import Enum

import rclpy
from action_msgs.msg import GoalStatus
from geographic_msgs.msg import GeoPoint
from navigation_interfaces.action import NavigateToGPS
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix

ERROR_NAMES = {
    getattr(NavigateToGPS.Result, name): name
    for name in (
        "NONE",
        "NO_GPS_FIX",
        "CONVERSION_FAILED",
        "NAV2_REJECTED",
        "NAV2_FAILED",
        "GOAL_BLOCKED",
        "TIMED_OUT",
    )
}


class MissionState(Enum):
    """Enum class for mission state"""

    IDLE = 0
    NAVIGATING_GPS = 1
    COMPLETE = 2
    FAILED = 3


class NavigationNode(Node):
    """Node to sequence mission goals through the navigation action servers"""

    def __init__(self):
        super().__init__("navigation_node")
        self.state = MissionState.IDLE
        # Latest goal request, and its handle once accepted. Responses for anything older belong
        # to goals the server has already replaced, so they're ignored.
        self._request = None
        self._goal_handle = None

        self._gps_client = ActionClient(self, NavigateToGPS, "navigate_to_gps")
        self.create_subscription(NavSatFix, "/goal/gnss", self._on_gnss_goal, 10)

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
        if not self._gps_client.server_is_ready():
            self.get_logger().error("The navigate_to_gps action server isn't available")
            self._set_state(MissionState.FAILED)
            return

        self.get_logger().info(f"GNSS goal ({fix.latitude:.7f}, {fix.longitude:.7f})")
        goal = NavigateToGPS.Goal(
            target=GeoPoint(latitude=fix.latitude, longitude=fix.longitude, altitude=fix.altitude)
        )
        # The server replaces any goal in progress, so there's nothing to cancel first
        self._goal_handle = None
        self._request = self._gps_client.send_goal_async(
            goal, feedback_callback=self._on_gps_feedback
        )
        self._request.add_done_callback(self._on_goal_response)
        self._set_state(MissionState.NAVIGATING_GPS)

    def _on_goal_response(self, request):
        if request is not self._request:
            return
        goal_handle = request.result()
        if not goal_handle.accepted:
            self.get_logger().error("navigate_to_gps rejected the goal")
            self._set_state(MissionState.FAILED)
            return
        self._goal_handle = goal_handle
        goal_handle.get_result_async().add_done_callback(
            lambda future: self._on_result(goal_handle, future)
        )

    def _on_gps_feedback(self, msg):
        self.get_logger().info(
            f"{msg.feedback.distance_remaining:.1f} m to go", throttle_duration_sec=5.0
        )

    def _on_result(self, goal_handle, future):
        if goal_handle is not self._goal_handle:
            return
        self._goal_handle = None
        response = future.result()
        if response.status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info("GNSS goal reached")
            self._set_state(MissionState.COMPLETE)
        elif response.status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info("GNSS goal canceled")
            self._set_state(MissionState.IDLE)
        else:
            result = response.result
            error = ERROR_NAMES.get(result.error_code, str(result.error_code))
            self.get_logger().error(f"GNSS goal failed ({error}): {result.error_msg}")
            self._set_state(MissionState.FAILED)


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
