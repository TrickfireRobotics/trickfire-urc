"""
This module contains the logic for setting up and managing nodes controlling the AR Tag Detection
system.

Its classes include TagDetectionLogic and ArTagDetectionNode.
"""

from __future__ import annotations

import sys

import cv2 as cv
import numpy as np
import rclpy
from cv_bridge import CvBridge
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
        logger: RcutilsLogger | None = None,
    ) -> None:
        self._detected_tag_type = cv.aruco.getPredefinedDictionary(wanted_tag_type)
        self._detected_tag_params = cv.aruco.DetectorParameters()
        self.bridge = CvBridge()
        self._logger: RcutilsLogger = logger or rclpy.logging.get_logger("tag_detection_logic")

    def feedFrame(
        self, frame: CompressedImage
    ) -> tuple[CompressedImage, Int32MultiArray, Int32MultiArray]:
        """Detects ArUco tags in the given compressed frame and annotates it."""
        converted_frame = self.bridge.compressed_imgmsg_to_cv2(frame, desired_encoding="bgr8")
        corners, ids, _ = cv.aruco.detectMarkers(
            converted_frame, self._detected_tag_type, parameters=self._detected_tag_params
        )

        detected_ids = Int32MultiArray()
        detected_corners = Int32MultiArray()
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
                self._logger.info(f"Detected tag: {marker_id} at corners: {tl} {tr} {br} {bl}")

        compressed_image = self.bridge.cv2_to_compressed_imgmsg(converted_frame, dst_format="jpg")
        return compressed_image, detected_ids, detected_corners

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

    def __init__(self, camera_id: int = 0) -> None:
        node_name = f"ar_tag_detection_node_{camera_id}"
        super().__init__(node_name)

        self._tag_detection_logic = TagDetectionLogic(
            cv.aruco.DICT_4X4_50,
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

        self.get_logger().info(f"AR Tag Node initialized. Subscribed to: {image_topic}")

    def frame_callback(self, msg: CompressedImage) -> None:
        """Callback to rate-limit frames and forward them to detection logic."""
        now = self.get_clock().now()
        dt_seconds = (now - self._last_process_time).nanoseconds / 1e9
        if dt_seconds < self._min_process_interval:
            return
        self._last_process_time = now

        frame, ids_msg, corners_msg = self._tag_detection_logic.feedFrame(msg)

        frame.header.stamp = now.to_msg()
        frame.header.frame_id = "ar_tag_detection_optical_frame"

        self._tag_publisher.publish(frame)
        self._tag_id_publisher.publish(ids_msg)
        self._tag_corners_publisher.publish(corners_msg)


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

    node = ArTagDetectionNode(camera_id=camera_id)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
