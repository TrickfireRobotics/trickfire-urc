"""
This module contains the logic for setting up and managing nodes controlling the AR Tag Detection
system.

Its classes include TagDetectionLogic and ArTagDetectionNode.
"""

from __future__ import annotations

import json
import sys
from os import path

import cv2 as cv
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Pose, PoseArray
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Int32MultiArray

# Type alias representing an (x, y) pixel coordinate
Point2D = tuple[int, int]


class TagDetectionLogic:
    """Processes image frames to identify and draw ArUco fiducial markers."""

    def __init__(
        self,
        wanted_tag_type: int,
        marker_size: float,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
        logger: RcutilsLogger | None = None,
    ) -> None:
        self._detected_tag_type = cv.aruco.getPredefinedDictionary(wanted_tag_type)
        self._detected_tag_params = cv.aruco.DetectorParameters()
        self._detector = cv.aruco.ArucoDetector(self._detected_tag_type, self._detected_tag_params)

        self.bridge = CvBridge()
        self._logger: RcutilsLogger = logger or rclpy.logging.get_logger("tag_detection_logic")

        self._marker_size = marker_size
        self._camera_matrix = camera_matrix
        self._dist_coeffs = dist_coeffs

        half_marker_size = marker_size / 2.0
        self.marker_points = np.array(
            [
                [-half_marker_size, half_marker_size, 0],
                [half_marker_size, half_marker_size, 0],
                [half_marker_size, -half_marker_size, 0],
                [-half_marker_size, -half_marker_size, 0],
            ],
            dtype=np.float32,
        )

    def feedFrame(
        self, frame: CompressedImage
    ) -> tuple[CompressedImage, Int32MultiArray, Int32MultiArray, list[Pose]]:
        """Detects ArUco tags in the given compressed frame and annotates it."""
        converted_frame = self.bridge.compressed_imgmsg_to_cv2(frame, desired_encoding="bgr8")

        corners, ids, _ = self._detector.detectMarkers(converted_frame)

        detected_ids = Int32MultiArray()
        detected_corners = Int32MultiArray()
        pose_list: list[Pose] = []

        detected_ids.data = []
        detected_corners.data = []

        if ids is not None and len(corners) > 0:
            cv.aruco.drawDetectedMarkers(converted_frame, corners, ids)
            ids_flat = ids.flatten()

            for marker_corners, marker_id in zip(corners, ids_flat):
                tl, tr, br, bl = self._handleValidTagCorners(marker_corners)
                detected_ids.data.append(int(marker_id))
                detected_corners.data.extend(
                    [tl[0], tl[1], tr[0], tr[1], br[0], br[1], bl[0], bl[1]]
                )

                success, rvec, tvec = cv.solvePnP(
                    self.marker_points, marker_corners, self._camera_matrix, self._dist_coeffs
                )

                if success:
                    # Convert 3D rotation vector to a 3x3 rotation matrix
                    rot_matrix, _ = cv.Rodrigues(rvec)

                    # Convert 3x3 matrix into a standard [x, y, z, w] quaternion array
                    q = self._rotationMatrixToQuaternion(rot_matrix)

                    # Build geometry_msgs/Pose object
                    pose = Pose()
                    pose.position.x = float(tvec[0][0])
                    pose.position.y = float(tvec[1][0])
                    pose.position.z = float(tvec[2][0])
                    pose.orientation.x = q[0]
                    pose.orientation.y = q[1]
                    pose.orientation.z = q[2]
                    pose.orientation.w = q[3]

                    pose_list.append(pose)

                    cv.drawFrameAxes(
                        converted_frame,
                        self._camera_matrix,
                        self._dist_coeffs,
                        rvec,
                        tvec,
                        self._marker_size,
                    )

        compressed_image = self.bridge.cv2_to_compressed_imgmsg(converted_frame, dst_format="jpg")
        return compressed_image, detected_ids, detected_corners, pose_list

    def _rotationMatrixToQuaternion(self, matrix: np.ndarray) -> np.ndarray:
        """Converts a 3x3 rotation matrix into a [qx, qy, qz, qw] unit quaternion."""
        # Unpack the 3x3 matrix
        m00, m01, m02 = matrix[0][0], matrix[0][1], matrix[0][2]
        m10, m11, m12 = matrix[1][0], matrix[1][1], matrix[1][2]
        m20, m21, m22 = matrix[2][0], matrix[2][1], matrix[2][2]

        # Calculate the sum of the main diagonal elements
        trace = m00 + m11 + m22

        # Safe to compute the scalar part (qw) first, the total rotation is way less then 180 degs
        if trace > 0:
            scale_factor = np.sqrt(trace + 1.0) * 2
            qw = 0.25 * scale_factor
            qx = (m21 - m12) / scale_factor
            qy = (m02 - m20) / scale_factor
            qz = (m10 - m01) / scale_factor

        # X-axis rotation dominates (m00 is the largest diagonal element),
        # the tag is rotated primarily around the local x-axis, near 180 degs
        elif (m00 > m11) and (m00 > m22):
            scale_factor = np.sqrt(1.0 + m00 - m11 - m22) * 2
            qw = (m21 - m12) / scale_factor
            qx = 0.25 * scale_factor
            qy = (m01 + m10) / scale_factor
            qz = (m02 + m20) / scale_factor

        # Y-axis rotation dominates (m11 is the largest diagonal element)
        # the tag is rotated primarily around the local y-axis, near 180 degs
        elif m11 > m22:
            scale_factor = np.sqrt(1.0 + m11 - m00 - m22) * 2
            qw = (m02 - m20) / scale_factor
            qx = (m01 + m10) / scale_factor
            qy = 0.25 * scale_factor
            qz = (m12 + m21) / scale_factor

        # Z-axis rotation dominates (m22 is the largest diagonal element)
        # the tag is rotated primarily around the local z-axis, near 180 degs
        else:
            scale_factor = np.sqrt(1.0 + m22 - m00 - m11) * 2
            qw = (m10 - m01) / scale_factor
            qx = (m02 + m20) / scale_factor
            qy = (m12 + m21) / scale_factor
            qz = 0.25 * scale_factor

        return np.array([qx, qy, qz, qw])

    def _handleValidTagCorners(
        self, corners: np.ndarray
    ) -> tuple[Point2D, Point2D, Point2D, Point2D]:
        """Processes the corner array of a detected tag into integer coordinate tuples."""
        reshaped_corners = corners.reshape((4, 2))
        top_left, top_right, bottom_right, bottom_left = reshaped_corners

        return (
            (int(top_left[0]), int(top_left[1])),
            (int(top_right[0]), int(top_right[1])),
            (int(bottom_right[0]), int(bottom_right[1])),
            (int(bottom_left[0]), int(bottom_left[1])),
        )


class ArTagDetectionNode(Node):
    """ROS 2 Node that manages camera subscriptions and publishes detected tag data."""

    def __init__(
        self, camera_id: int = 0, camera_calibration_file: str = "camera_calibration.json"
    ) -> None:
        node_name = f"ar_tag_detection_node_{camera_id}"
        super().__init__(node_name)

        with open(camera_calibration_file, "r") as file:
            calibration_data = json.load(file)

        camera_matrix = np.array(calibration_data["camera_matrix"], dtype=np.float32)
        dist_coeffs = np.array(calibration_data["dist_coeffs"], dtype=np.float32)

        marker_size = 0.05  # Marker size in meters

        self._tag_detection_logic = TagDetectionLogic(
            cv.aruco.DICT_4X4_50,
            marker_size,
            camera_matrix,
            dist_coeffs,
            logger=self.get_logger(),
        )

        self.declare_parameter("image_topic", f"/camera_{camera_id}/image/compressed")
        image_topic = self.get_parameter("image_topic").get_parameter_value().string_value

        self.declare_parameter("process_rate_hz", 2.0)
        process_rate = self.get_parameter("process_rate_hz").get_parameter_value().double_value
        self._min_process_interval = 1.0 / process_rate if process_rate > 0 else 0.0
        self._last_process_time = self.get_clock().now()

        queue_size = 10

        self.tag_detection_topic = f"/camera_{camera_id}/tags"
        self.tag_id_topic = f"/camera_{camera_id}/tags/ids"
        self.tag_corners_topic = f"/camera_{camera_id}/tags/tag_corners"
        self.tag_poses_topic = f"/camera_{camera_id}/tags/tag_poses"

        self._camera_subscriber = self.create_subscription(
            CompressedImage, image_topic, self.frame_callback, queue_size
        )
        self._tag_publisher = self.create_publisher(
            CompressedImage, self.tag_detection_topic, queue_size
        )
        self._tag_id_publisher = self.create_publisher(
            Int32MultiArray, self.tag_id_topic, queue_size
        )
        self._tag_corners_publisher = self.create_publisher(
            Int32MultiArray, self.tag_corners_topic, queue_size
        )
        self._tag_poses_publisher = self.create_publisher(
            PoseArray, self.tag_poses_topic, queue_size
        )

        self.get_logger().info(f"AR Tag Node initialized. Subscribed to: {image_topic}")

    def frame_callback(self, msg: CompressedImage) -> None:
        """Callback to rate-limit frames and forward them to detection logic."""
        now = self.get_clock().now()
        dt_seconds = (now - self._last_process_time).nanoseconds / 1e9
        if dt_seconds < self._min_process_interval:
            return
        self._last_process_time = now

        frame, ids_msg, corners_msg, pose_list = self._tag_detection_logic.feedFrame(msg)

        timestamp_msg = now.to_msg()
        optical_frame_id = "ar_tag_detection_optical_frame"

        frame.header.stamp = timestamp_msg
        frame.header.frame_id = optical_frame_id

        self._tag_publisher.publish(frame)
        self._tag_id_publisher.publish(ids_msg)
        self._tag_corners_publisher.publish(corners_msg)

        poses_msg = PoseArray()
        poses_msg.header.stamp = timestamp_msg
        poses_msg.header.frame_id = optical_frame_id
        poses_msg.poses = pose_list

        self._tag_poses_publisher.publish(poses_msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)

    camera_id = 0
    cli_args = sys.argv if args is None else args

    for i, arg in enumerate(cli_args):
        if arg == "--camera-id" and i + 1 < len(cli_args):
            try:
                camera_id = int(cli_args[i + 1])
            except ValueError:
                pass
        elif arg == "--calibration-file" and i + 1 < len(cli_args):
            calibration_file = cli_args[i + 1]
            if calibration_file is None:
                if path.exists("camera_calibration.json"):
                    camera_calibration_file = "camera_calibration.json"
                else:
                    raise ValueError(
                        "Calibration file path cannot be None. Provide a valid path to"
                        "the camera calibration JSON file via --calibration-file <path>"
                        "during node launch."
                    )
            else:
                camera_calibration_file = calibration_file
    node = ArTagDetectionNode(camera_id=camera_id, calibration_file=camera_calibration_file)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
