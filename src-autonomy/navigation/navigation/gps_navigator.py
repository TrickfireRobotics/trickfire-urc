"""Serve navigate_to_gps: drive to a lat/lon by converting it to a map pose for Nav2."""

import math

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose, NavigateToPose
from nav_msgs.msg import OccupancyGrid, Odometry
from navigation_interfaces.action import NavigateToGPS
from rclpy.action import ActionClient, ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.task import Future
from rclpy.time import Time
from robot_localization.srv import FromLL
from tf2_ros import Buffer, TransformException, TransformListener

Result = NavigateToGPS.Result

STATUS_NAMES = {GoalStatus.STATUS_CANCELED: "canceled", GoalStatus.STATUS_ABORTED: "aborted"}
# Planner errors that mean Nav2 can't find a way to the goal, as opposed to failing on the way
NO_PATH_CODES = (ComputePathToPose.Result.GOAL_OCCUPIED, ComputePathToPose.Result.NO_VALID_PATH)
# OccupancyGrid value of the costmap's inscribed band. The rover's centre can't go there, or on
# the obstacles above it, so the planner treats both as walls.
INSCRIBED_COST = 99
# How far (m) from a goal to look for open ground. Larger enclosures are left to the planner.
ENCLOSURE_SEARCH_RADIUS = 3.0


def _goal_enclosed(grid: OccupancyGrid, x, y, tolerance, robot=None) -> bool:
    """Whether obstacles seen so far cut (x, y) off from open ground.

    Follows the planner's rules: it may end anywhere within tolerance of the goal, and unknown
    cells are passable. The goal's own cell can't answer this, as the inside of a rock is never
    seen and stays unknown. So this searches outward from the cells around the goal and reports
    an enclosure if that search can't get out. robot is the rover's (x, y): reaching it counts as
    getting out. A goal off the grid isn't enclosed; Nav2 reports those itself.
    """
    resolution = grid.info.resolution
    origin = grid.info.origin.position
    width, height = grid.info.width, grid.info.height
    col = int((x - origin.x) / resolution)
    row = int((y - origin.y) / resolution)
    if not (0 <= col < width and 0 <= row < height):
        return False
    robot_cell = None
    if robot is not None:
        robot_cell = (
            int((robot[0] - origin.x) / resolution),
            int((robot[1] - origin.y) / resolution),
        )

    # Rounded because resolution is a float32, just over 0.1, which int() would cut a cell short
    reach = round(tolerance / resolution)
    limit = round(ENCLOSURE_SEARCH_RADIUS / resolution)
    data = grid.data
    frontier = [
        (c, r)
        for r in range(max(row - reach, 0), min(row + reach, height - 1) + 1)
        for c in range(max(col - reach, 0), min(col + reach, width - 1) + 1)
        if data[r * width + c] < INSCRIBED_COST
    ]
    seen = set(frontier)
    while frontier:
        c, r = frontier.pop()
        if (
            (c, r) == robot_cell
            or abs(c - col) >= limit
            or abs(r - row) >= limit
            or c in (0, width - 1)
            or r in (0, height - 1)
        ):
            return False
        for cell in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if cell not in seen and data[cell[1] * width + cell[0]] < INSCRIBED_COST:
                seen.add(cell)
                frontier.append(cell)
    return True


class GpsNavigator(Node):
    """Node to serve NavigateToGPS goals through Nav2's navigate_to_pose"""

    def __init__(self):
        super().__init__("gps_navigator")
        self.declare_parameter("base_frame", "base_footprint")
        self.base_frame = self.get_parameter("base_frame").value
        # Matches the planner's tolerance in nav2_params.yaml
        self.declare_parameter("planner_tolerance", 0.5)
        # Time allowed to reach a goal (s): timeout_base + timeout_per_metre * straight-line
        # distance. That's about 2.5x a 2:1 detour at 0.5 m/s, plus time for turns and recoveries.
        self.declare_parameter("timeout_base", 60.0)
        self.declare_parameter("timeout_per_metre", 10.0)

        # Frame that fromLL converts into, known once navsat_transform publishes GPS odometry.
        # It only does that once it has a datum; before then fromLL returns meaningless points
        # rather than an error.
        self._gps_frame = None
        # The goal being served and its Nav2 goal, once sent. One goal runs at a time.
        self._goal = None
        self._nav2_goal = None
        # Done once the last Nav2 goal sent has ended. Nav2 takes a goal sent while another is
        # running as a preemption and follows the old path until it next replans, up to a second
        # later, so it can arrive at the old goal and report the new one reached.
        self._nav2_ended = None
        self._costmap = None
        # The running Nav2 goal's target and time limit, and why _watch_nav2_goal stopped it:
        # (error code, message), or None if it hasn't
        self._target = None
        self._time_limit = None
        self._deadline = None
        self._stop_reason = None

        # execute awaits service and action responses, which can only arrive if their
        # callbacks are allowed to run alongside it
        group = ReentrantCallbackGroup()
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._from_ll = self.create_client(FromLL, "fromLL", callback_group=group)
        self._nav2 = ActionClient(self, NavigateToPose, "navigate_to_pose", callback_group=group)
        self.create_subscription(
            Odometry, "/odometry/gps", self._on_gps_odometry, 1, callback_group=group
        )
        self.create_subscription(
            OccupancyGrid,
            "/global_costmap/costmap",
            self._on_costmap,
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL),
            callback_group=group,
        )
        self.create_timer(1.0, self._watch_nav2_goal, callback_group=group)
        self._server = ActionServer(
            self,
            NavigateToGPS,
            "navigate_to_gps",
            execute_callback=self._execute,
            handle_accepted_callback=self._on_accepted,
            cancel_callback=self._on_cancel,
            callback_group=group,
        )

    def _on_gps_odometry(self, msg: Odometry):
        if self._gps_frame is None:
            self.get_logger().info(f"GPS datum set, accepting goals in '{msg.header.frame_id}'")
        self._gps_frame = msg.header.frame_id

    def _on_costmap(self, msg: OccupancyGrid):
        self._costmap = msg

    def _on_accepted(self, goal_handle):
        # A new goal replaces the current one, which mustn't keep driving if the new one fails
        if self._goal is not None and self._goal.is_active:
            self._goal.abort()
        if self._nav2_goal is not None:
            self._nav2_goal.cancel_goal_async()
        self._goal = goal_handle
        self._nav2_goal = None
        goal_handle.execute()

    def _on_cancel(self, goal_handle):
        if goal_handle is self._goal and self._nav2_goal is not None:
            self._nav2_goal.cancel_goal_async()
        return CancelResponse.ACCEPT

    async def _execute(self, goal_handle):
        result = Result()
        target = goal_handle.request.target

        if self._gps_frame is None:
            return self._abort(
                goal_handle,
                result,
                Result.NO_GPS_FIX,
                "No GPS datum yet. Drive a few metres so gps_heading_init can find the heading",
            )
        if not self._from_ll.service_is_ready():
            return self._abort(
                goal_handle, result, Result.CONVERSION_FAILED, "fromLL service isn't available"
            )
        response = await self._from_ll.call_async(FromLL.Request(ll_point=target))
        if self._interrupted(goal_handle):
            return self._end_interrupted(goal_handle, result)
        point = response.map_point
        if not (math.isfinite(point.x) and math.isfinite(point.y)):
            return self._abort(
                goal_handle, result, Result.CONVERSION_FAILED, f"fromLL returned {point}"
            )

        if not self._nav2.server_is_ready():
            return self._abort(goal_handle, result, Result.NAV2_REJECTED, "Nav2 isn't active")
        if self._nav2_ended is not None:
            # The goal this one replaced may still be running in Nav2. If another goal replaces
            # this one meanwhile, that one waits for it too.
            await self._nav2_ended
            if self._interrupted(goal_handle):
                return self._end_interrupted(goal_handle, result)
        if self._goal_walled_off(point):
            return self._abort(
                goal_handle, result, Result.GOAL_BLOCKED, self._walled_off_message(point)
            )
        self.get_logger().info(
            f"Navigating to ({target.latitude:.7f}, {target.longitude:.7f}), "
            f"({point.x:.2f}, {point.y:.2f}) in {self._gps_frame}"
        )
        nav2_result = await self._run_nav2_goal(goal_handle, point)
        if nav2_result is None:
            return self._abort(goal_handle, result, Result.NAV2_REJECTED, "Nav2 rejected the goal")
        if goal_handle is self._goal:
            self._nav2_goal = None
        if nav2_result.status == GoalStatus.STATUS_SUCCEEDED and goal_handle.is_active:
            goal_handle.succeed()
            return result
        if self._interrupted(goal_handle):
            return self._end_interrupted(goal_handle, result)
        if self._stop_reason is not None:
            return self._abort(goal_handle, result, *self._stop_reason)
        if nav2_result.result.error_code in NO_PATH_CODES:
            return self._abort(
                goal_handle,
                result,
                Result.GOAL_BLOCKED,
                f"Nav2 found no path to ({point.x:.2f}, {point.y:.2f}): obstacles may block it",
            )
        status = STATUS_NAMES.get(nav2_result.status, f"ended with status {nav2_result.status}")
        details = nav2_result.result.error_msg or f"error code {nav2_result.result.error_code}"
        return self._abort(goal_handle, result, Result.NAV2_FAILED, f"Nav2 {status}: {details}")

    async def _run_nav2_goal(self, goal_handle, point):
        """Send point to Nav2 and wait for that goal to end, which later goals wait on.

        Returns the goal's result, or None if Nav2 rejected it.
        """
        ended = self._nav2_ended = Future()
        robot = self._robot_position()
        distance = math.hypot(point.x - robot[0], point.y - robot[1]) if robot else 0.0
        self._target = point
        self._time_limit = (
            self.get_parameter("timeout_base").value
            + self.get_parameter("timeout_per_metre").value * distance
        )
        self._deadline = self.get_clock().now() + Duration(seconds=self._time_limit)
        self._stop_reason = None
        try:
            nav2_goal = await self._nav2.send_goal_async(
                NavigateToPose.Goal(pose=self._goal_pose(point)),
                feedback_callback=lambda msg: self._on_nav2_feedback(goal_handle, msg),
            )
            if not nav2_goal.accepted:
                return None
            # Canceled or replaced while being sent, so _on_cancel or _on_accepted couldn't
            # cancel it in Nav2
            if self._interrupted(goal_handle):
                nav2_goal.cancel_goal_async()
            else:
                self._nav2_goal = nav2_goal
            return await nav2_goal.get_result_async()
        finally:
            ended.set_result(None)

    def _watch_nav2_goal(self):
        """Stop the running Nav2 goal if time runs out or obstacles turn out to block its target.

        Goals are often beyond the camera's range when sent, so obstacles around them may only
        be seen on the way. Left to itself, Nav2 keeps probing such a goal for minutes.
        """
        if self._nav2_goal is None or self._stop_reason is not None:
            return
        if self.get_clock().now() > self._deadline:
            self._stop_reason = (
                Result.TIMED_OUT,
                f"Didn't reach ({self._target.x:.2f}, {self._target.y:.2f}) "
                f"in {self._time_limit:.0f} s",
            )
        elif self._goal_walled_off(self._target):
            self._stop_reason = (Result.GOAL_BLOCKED, self._walled_off_message(self._target))
        if self._stop_reason is not None:
            self._nav2_goal.cancel_goal_async()

    def _goal_walled_off(self, point) -> bool:
        if self._costmap is None:
            return False
        tolerance = self.get_parameter("planner_tolerance").value
        return _goal_enclosed(self._costmap, point.x, point.y, tolerance, self._robot_position())

    def _walled_off_message(self, point) -> str:
        tolerance = self.get_parameter("planner_tolerance").value
        return (
            f"Goal ({point.x:.2f}, {point.y:.2f}) is inside or walled off by obstacles: "
            f"nothing within {tolerance:g} m of it can be reached"
        )

    def _robot_position(self):
        """The rover's (x, y) in the GPS frame, or None if it isn't known"""
        try:
            robot = self._tf_buffer.lookup_transform(
                self._gps_frame, self.base_frame, Time()
            ).transform.translation
        except TransformException as e:
            self.get_logger().warning(f"No robot pose: {e}", throttle_duration_sec=5.0)
            return None
        return robot.x, robot.y

    def _goal_pose(self, point) -> PoseStamped:
        """Pose at point, facing the way the rover approaches it.

        GPS goals have no heading, but Nav2 turns to match the goal's yaw on arrival.
        """
        pose = PoseStamped()
        pose.header.frame_id = self._gps_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = point.x
        pose.pose.position.y = point.y
        robot = self._robot_position()
        yaw = math.atan2(point.y - robot[1], point.x - robot[0]) if robot else 0.0
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def _on_nav2_feedback(self, goal_handle, msg):
        if goal_handle.is_active:
            feedback = NavigateToGPS.Feedback(distance_remaining=msg.feedback.distance_remaining)
            goal_handle.publish_feedback(feedback)

    @staticmethod
    def _interrupted(goal_handle) -> bool:
        """Whether the goal was canceled or replaced while waiting on something"""
        return goal_handle.is_cancel_requested or not goal_handle.is_active

    @staticmethod
    def _end_interrupted(goal_handle, result):
        if goal_handle.is_active:
            goal_handle.canceled()
        else:
            result.error_msg = "Replaced by a newer goal"
        return result

    def _abort(self, goal_handle, result, error_code, message):
        self.get_logger().warning(message)
        result.error_code = error_code
        result.error_msg = message
        if goal_handle.is_active:
            goal_handle.abort()
        return result


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
