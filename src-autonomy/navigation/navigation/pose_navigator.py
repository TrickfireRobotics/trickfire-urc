"""Serve navigate_to_target: drive to a pose given in any TF frame, such as one the camera found."""

import math

import rclpy
from navigation_interfaces.action import NavigateToTarget
from rclpy.time import Time
from tf2_geometry_msgs import do_transform_pose
from tf2_ros import TransformException

from navigation.nav2_navigator import GoalError, Nav2Navigator

Result = NavigateToTarget.Result
# A target stamped within this many seconds of now may be placed with the latest transform when
# there's none at its stamp yet: a detection can be stamped a few milliseconds past the latest
# EKF output, and the rover goes nowhere in that time.
FRESH_TARGET_S = 1.0


def _finite(pose) -> bool:
    p, q = pose.position, pose.orientation
    return all(math.isfinite(v) for v in (p.x, p.y, p.z, q.x, q.y, q.z, q.w))


class PoseNavigator(Nav2Navigator):
    """Node to serve NavigateToTarget goals through Nav2's navigate_to_pose"""

    def __init__(self):
        super().__init__("pose_navigator", NavigateToTarget, "navigate_to_target")
        # Nav2's global frame, which targets are placed in
        self.declare_parameter("global_frame", "map")
        self.global_frame = self.get_parameter("global_frame").value
        # Arrive facing the target's own orientation rather than the way the rover approaches
        # it. Off by default: a detected object's orientation usually means nothing.
        self.declare_parameter("use_target_orientation", False)

    async def _resolve(self, request):
        target = request.target
        frame = target.header.frame_id
        position = target.pose.position
        description = f"({position.x:.2f}, {position.y:.2f}) in '{frame}'"
        if not frame:
            raise GoalError(Result.TRANSFORM_FAILED, "Target has no frame_id")
        # Every field: a transform out of a tilted frame mixes z into x and y
        if not _finite(target.pose):
            raise GoalError(Result.TRANSFORM_FAILED, f"Target {description} isn't finite")
        pose = target.pose
        if frame != self.global_frame:
            pose = do_transform_pose(pose, self._transform_from(frame, target.header.stamp))
            if not _finite(pose):
                raise GoalError(
                    Result.TRANSFORM_FAILED, f"Target {description} isn't finite in map"
                )
        yaw = None
        if self.get_parameter("use_target_orientation").value:
            q = pose.orientation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return pose.position.x, pose.position.y, yaw, description

    def _transform_from(self, frame, stamp):
        """The transform from frame into the global frame at stamp, or the latest if it's fresh"""
        at = Time.from_msg(stamp)
        try:
            return self._tf_buffer.lookup_transform(self.global_frame, frame, at)
        except TransformException as e:
            age = abs((self.get_clock().now() - at).nanoseconds) * 1e-9
            if age > FRESH_TARGET_S:
                raise GoalError(
                    Result.TRANSFORM_FAILED,
                    f"Can't place a target from '{frame}' in '{self.global_frame}': {e}",
                ) from e
        try:
            return self._tf_buffer.lookup_transform(self.global_frame, frame, Time())
        except TransformException as e:
            raise GoalError(
                Result.TRANSFORM_FAILED,
                f"Can't place a target from '{frame}' in '{self.global_frame}': {e}",
            ) from e


def main(args=None):
    rclpy.init(args=args)
    node = PoseNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
