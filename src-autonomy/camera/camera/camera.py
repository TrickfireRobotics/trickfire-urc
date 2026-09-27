import sys
import threading

import cv2 as cv
import rclpy
from cv2.typing import MatLike
from cv_bridge import CvBridge
from lib.color_codes import ColorCodes, colorStr
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Int32MultiArray, String


def getCameras() -> list[int]:
    """
    Returns a list of active camera ID's
    """

    NON_WORKING_PORT_THRESHOLD = 6

    # Property ID's for width and height of the camera feed
    WIDTH_PROPERTY_ID = 3
    HEIGHT_PROPERTY_ID = 4

    non_working_ports = 0
    dev_port = 0
    working_ports = []

    while non_working_ports < NON_WORKING_PORT_THRESHOLD:
        camera = cv.VideoCapture(dev_port)
        if not camera.isOpened():
            non_working_ports += 1
        else:
            is_reading, img = camera.read()
            _ = camera.get(WIDTH_PROPERTY_ID)
            _ = camera.get(HEIGHT_PROPERTY_ID)
            if is_reading:
                working_ports.append(dev_port)
            camera.release()
        dev_port += 1

    return working_ports


class CameraNode(Node):
    """A node for handling camera operations."""

    def _initializeTagDetection(self) -> None:
        """
        Initializes the tag detection system.
        """

        WANTED_TAG_TYPE = cv.aruco.DICT_4X4_50

        self._detected_tag_type = cv.aruco.getPredefinedDictionary(WANTED_TAG_TYPE)
        self._detected_tag_params = cv.aruco.DetectorParameters()

    def __init__(self, topicName: str, camera: int) -> None:

        PUBLISHER_QUEUE_SIZE = 10
        FRAME_PUBLISH_TIMER_PERIOD_SECONDS = 0.1
        TAG_DETECTION_TIMER_PERIOD_SECONDS = 0.5

        self.FRAME_PUBLISHER_TOPIC = f"{topicName}/raw"
        self.TAG_DETECTION_TOPIC = f"{topicName}/tags"
        self.TAG_ID_TOPIC = f"{topicName}/tag_ids"
        self.TAG_CORNERS_TOPIC = f"{topicName}/tag_corners"

        super().__init__(f"camera_node_{camera}")
        self._initializeTagDetection()

        self.get_logger().info(colorStr("Launching Camera Node", ColorCodes.GREEN_OK))

        self._framePublisher = self.create_publisher(
            CompressedImage, self.FRAME_PUBLISHER_TOPIC, PUBLISHER_QUEUE_SIZE
        )
        self.get_logger().info(
            colorStr(f"Created Publisher: {self.FRAME_PUBLISHER_TOPIC}", ColorCodes.GREEN_OK)
        )

        self._tagPublisher = self.create_publisher(
            CompressedImage, self.TAG_DETECTION_TOPIC, PUBLISHER_QUEUE_SIZE
        )
        self.get_logger().info(
            colorStr(f"Created Publisher: {self.TAG_DETECTION_TOPIC}", ColorCodes.GREEN_OK)
        )

        self._tagIdPublisher = self.create_publisher(
            Int32MultiArray, self.TAG_ID_TOPIC, PUBLISHER_QUEUE_SIZE
        )
        self.get_logger().info(
            colorStr(f"Created Publisher: {self.TAG_ID_TOPIC}", ColorCodes.GREEN_OK)
        )

        self._tagCornersPublisher = self.create_publisher(
            Int32MultiArray, self.TAG_CORNERS_TOPIC, PUBLISHER_QUEUE_SIZE
        )
        self.get_logger().info(
            colorStr(f"Created Publisher: {self.TAG_CORNERS_TOPIC}", ColorCodes.GREEN_OK)
        )

        self.frameTimer = self.create_timer(
            FRAME_PUBLISH_TIMER_PERIOD_SECONDS, self._publishCameraFrame
        )
        self.tagTimer = self.create_timer(TAG_DETECTION_TIMER_PERIOD_SECONDS, self._detectTags)

        self.frameCapture = cv.VideoCapture(camera)
        self.bridge = CvBridge()

        self._camera_lock = threading.Lock()

        self._camera_id = camera
        self.declare_parameter("camera_id", camera)

    def _publishCameraFrame(self) -> None:
        """
        Callback function to publish a camera frame to the specified topic.
        """
        with self._camera_lock:
            ret, frame = self.frameCapture.read()

        if ret:
            msg = self.bridge.cv2_to_compressed_imgmsg(frame, dst_format="jpg")
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = f"camera_{self._camera_id}_optical_frame"

            self._framePublisher.publish(msg)

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

    def _detectTags(self) -> None:
        """
        Callback function to detect tags in the camera frame.
        """
        with self._camera_lock:
            ret, frame = self.frameCapture.read()

        if not ret or frame is None:
            return

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

            for markerCorner, markerID in zip(corners, ids_flat):
                tl, tr, br, bl = self._calculateValidTagCorners(markerCorner)

                id_msg.data.append(int(markerID))
                corners_msg.data.extend([tl[0], tl[1], tr[0], tr[1], br[0], br[1], bl[0], bl[1]])

            img_msg = self.bridge.cv2_to_compressed_imgmsg(frame, dst_format="jpg")
            img_msg.header.stamp = self.get_clock().now().to_msg()
            img_msg.header.frame_id = f"camera_{self._camera_id}_optical_frame"

            self._tagPublisher.publish(img_msg)
            self._tagIdPublisher.publish(id_msg)
            self._tagCornersPublisher.publish(corners_msg)

    def destroy_node(self) -> None:
        """
        Ensures the camera hardware is released when the node is shut down.
        """
        if hasattr(self, "frameCapture") and self.frameCapture.isOpened():
            self.frameCapture.release()
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """
    Entry point for the camera node.
    """

    rclpy.init(args=args)

    try:
        executor = MultiThreadedExecutor()
        nodes = []
        camera_num = 0

        for camera in getCameras():
            node = CameraNode(f"/camera_{camera_num}/image", camera)
            nodes.append(node)
            executor.add_node(node)
            camera_num += 1

        try:
            executor.spin()
        finally:
            executor.shutdown()
            for node in nodes:
                node.destroy_node()
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
