"""Relay the simulator's ground-truth odometry as odom -> base_footprint.

Stands in for robot_localization's EKF in simulation: it publishes the same odometry topic
and transform, so Nav2 needs no changes when the EKF replaces it.
"""

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


def _rotate(q, v):
    """Rotate vector v by the unit quaternion q."""
    t = (
        2.0 * (q.y * v[2] - q.z * v[1]),
        2.0 * (q.z * v[0] - q.x * v[2]),
        2.0 * (q.x * v[1] - q.y * v[0]),
    )
    return (
        v[0] + q.w * t[0] + q.y * t[2] - q.z * t[1],
        v[1] + q.w * t[1] + q.z * t[0] - q.x * t[2],
        v[2] + q.w * t[2] + q.x * t[1] - q.y * t[0],
    )


class GroundTruthOdom(Node):
    """Node to republish ground-truth base_link odometry about base_footprint"""

    def __init__(self):
        super().__init__("ground_truth_odom")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_footprint")
        # Position of base_link in base_frame. Must match the static transform in the launch file.
        self.declare_parameter("base_link_offset", [0.0, 0.0, 0.0])
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        # The simulator reports base_link; this is base_frame's position relative to it
        self._offset = tuple(-v for v in self.get_parameter("base_link_offset").value)

        self._odom_pub = self.create_publisher(Odometry, "/odometry/filtered", 10)
        self._tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(Odometry, "/chassis/ground_truth/odometry", self._on_odom, 10)

    def _on_odom(self, msg: Odometry):
        pose = msg.pose.pose
        dx, dy, dz = _rotate(pose.orientation, self._offset)

        odom = Odometry()
        odom.header.stamp = msg.header.stamp
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = pose.position.x + dx
        odom.pose.pose.position.y = pose.position.y + dy
        odom.pose.pose.position.z = pose.position.z + dz
        odom.pose.pose.orientation = pose.orientation
        odom.pose.covariance = msg.pose.covariance

        # Twist is in the body frame; a point offset by r on a rigid body moves at v + w x r
        v, w, r = msg.twist.twist.linear, msg.twist.twist.angular, self._offset
        odom.twist.twist.linear.x = v.x + w.y * r[2] - w.z * r[1]
        odom.twist.twist.linear.y = v.y + w.z * r[0] - w.x * r[2]
        odom.twist.twist.linear.z = v.z + w.x * r[1] - w.y * r[0]
        odom.twist.twist.angular = w
        odom.twist.covariance = msg.twist.covariance
        self._odom_pub.publish(odom)

        transform = TransformStamped()
        transform.header = odom.header
        transform.child_frame_id = self.base_frame
        transform.transform.translation.x = odom.pose.pose.position.x
        transform.transform.translation.y = odom.pose.pose.position.y
        transform.transform.translation.z = odom.pose.pose.position.z
        transform.transform.rotation = pose.orientation
        self._tf_broadcaster.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = GroundTruthOdom()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
