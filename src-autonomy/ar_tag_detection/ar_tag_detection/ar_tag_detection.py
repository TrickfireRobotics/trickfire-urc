"""
This module contains the logic for setting up and managing nodes controlling the AR Tag Detection
system

It's classes include the ArTagDetectionNode
"""

import sys

import cv2 as cv
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Int32MultiArray


class ArTagDetectionNode(Node):
    def __init__(self, camera_id: int = 0) -> None:
        node_name = f"ar_tag_detection_node_{camera_id}"
        super().__init__(node_name)

        self.declare_parameter("image_topic", f"/camera_{camera_id}/image/compressed")
        image_topic = self.get_parameter("image_topic").get_parameter_value().string_value

        self.declare_parameter("process_rate_hz", 2.0)
        process_rate = self.get_parameter("process_rate_hz").get_parameter_value().double_value
        self._min_process_interval = 1.0 / process_rate if process_rate > 0 else 0.0
        self._last_process_time = self.get_clock().now()

        WANTED_TAG_TYPE = cv.aruco.DICT_4X4_50
        PUBLISHER_QUEUE_SIZE = 10
        SUBSCRIBER_QUEUE_SIZE = 10

        self.TAG_DETECTION_TOPIC = f"/camera_{camera_id}/tags"
        self.TAG_ID_TOPIC = f"/camera_{camera_id}/tags/ids"
        self.TAG_CORNERS_TOPIC = f"/camera_{camera_id}/tags/tag_corners"

        self._detected_tag_type = cv.aruco.getPredefinedDictionary(WANTED_TAG_TYPE)
        self._detected_tag_params = cv.aruco.DetectorParameters()

        self.bridge = CvBridge()

        self._CAMERA_SUBSCRIBER = self.create_subscription(
            CompressedImage, image_topic, self.detect_tags, SUBSCRIBER_QUEUE_SIZE
        )

        self._TAG_PUBLISHER = self.create_publisher(
            CompressedImage, self.TAG_DETECTION_TOPIC, PUBLISHER_QUEUE_SIZE
        )

        self._TAG_ID_PUBLISHER = self.create_publisher(
            Int32MultiArray, self.TAG_ID_TOPIC, PUBLISHER_QUEUE_SIZE
        )

        self._TAG_CORNERS_PUBLISHER = self.create_publisher(
            Int32MultiArray, self.TAG_CORNERS_TOPIC, PUBLISHER_QUEUE_SIZE
        )

        self.get_logger().info(f"AR Tag Node initialized. Subscribed to: {image_topic}")

    def detect_tags(self, msg: CompressedImage) -> None:
        """
        Detects any tag given in the provided image frame. Then publishes a drawn bounding box for
        the detected tag, it's ID, and the (x,y) location of the corner
        """

        now = self.get_clock().now()
        dt_seconds = (now - self._last_process_time).nanoseconds / 1e9
        if dt_seconds < self._min_process_interval:
            return  # Drop the frame if it's too soon
        self._last_process_time = now

        frame = self.bridge.compressed_imgmsg_to_cv2(msg, desired_encoding="bgr8")

        (corners, ids, _) = cv.aruco.detectMarkers(
            frame, self._detected_tag_type, parameters=self._detected_tag_params
        )

        if ids is not None and len(corners) > 0:
            cv.aruco.drawDetectedMarkers(frame, corners, ids)

            ids_flat = ids.flatten()
            id_msg = Int32MultiArray()
            corners_msg = Int32MultiArray()

            id_msg.data = []
            corners_msg.data = []

            for markerCorner, markerId in zip(corners, ids_flat):
                tl, tr, br, bl = self._calculateValidTagCorners(markerCorner)
                id_msg.data.append(int(markerId))
                corners_msg.data.extend([tl[0], tl[1], tr[0], tr[1], br[0], br[1], bl[0], bl[1]])

            img_msg = self.bridge.cv2_to_compressed_imgmsg(frame, dst_format="jpg")
            img_msg.header.stamp = self.get_clock().now().to_msg()
            img_msg.header.frame_id = "ar_tag_detection_optical_frame"

            self._TAG_PUBLISHER.publish(img_msg)
            self._TAG_ID_PUBLISHER.publish(id_msg)
            self._TAG_CORNERS_PUBLISHER.publish(corners_msg)

    def _calculateValidTagCorners(self, corners: list) -> tuple:
        """
        Calculates the corners of a valid detected tag
        """
        corners = corners.reshape((4, 2))
        (topLeft, topRight, bottomRight, bottomLeft) = corners

        topRight = (int(topRight[0]), int(topRight[1]))
        bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
        bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
        topLeft = (int(topLeft[0]), int(topLeft[1]))

        return topLeft, topRight, bottomRight, bottomLeft


def main(args: list[str] | None = None):
    rclpy.init(args=args)

    camera_id = 0
    if args is None:
        args = sys.argv

    for i, arg in enumerate(args):
        if arg == "--camera-id" and i + 1 < len(args):
            try:
                camera_id = int(args[i + 1])
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
