"""Serve navigate_to_gps: drive to a lat/lon by converting it to a map pose for Nav2."""

import math

import rclpy
from nav_msgs.msg import Odometry
from navigation_interfaces.action import NavigateToGPS
from robot_localization.srv import FromLL

from navigation.nav2_navigator import GoalError, Nav2Navigator

Result = NavigateToGPS.Result


class GpsNavigator(Nav2Navigator):
    """Node to serve NavigateToGPS goals through Nav2's navigate_to_pose"""

    def __init__(self):
        super().__init__("gps_navigator", NavigateToGPS, "navigate_to_gps")
        self._from_ll = self.create_client(FromLL, "fromLL", callback_group=self.group)
        # The frame fromLL converts into is known once navsat_transform publishes GPS odometry.
        # It only does that once it has a datum; before then fromLL returns meaningless points
        # rather than an error.
        self.create_subscription(
            Odometry, "/odometry/gps", self._on_gps_odometry, 1, callback_group=self.group
        )

    def _on_gps_odometry(self, msg: Odometry):
        if self.global_frame is None:
            self.get_logger().info(f"GPS datum set, accepting goals in '{msg.header.frame_id}'")
        self.global_frame = msg.header.frame_id

    async def _resolve(self, request):
        target = request.target
        if self.global_frame is None:
            raise GoalError(
                Result.NO_GPS_FIX,
                "No GPS datum yet. Drive a few metres so gps_heading_init can find the heading",
            )
        if not self._from_ll.service_is_ready():
            raise GoalError(Result.CONVERSION_FAILED, "fromLL service isn't available")
        response = await self._from_ll.call_async(FromLL.Request(ll_point=target))
        point = response.map_point
        if not (math.isfinite(point.x) and math.isfinite(point.y)):
            raise GoalError(Result.CONVERSION_FAILED, f"fromLL returned {point}")
        return point.x, point.y, None, f"({target.latitude:.7f}, {target.longitude:.7f})"


def main(args=None):
    rclpy.init(args=args)
    node = GpsNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
