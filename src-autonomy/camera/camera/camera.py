import sys

import cv2 as cv
import rclpy
from cv_bridge import CvBridge
from lib.color_codes import ColorCodes, colorStr
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String


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
        dev_port += 1

    return working_ports


class CameraNode(Node):
    """A node for handling camera operations."""

    def __init__(self, topicName: str, camera: int) -> None:

        PUBLISHER_QUEUE_SIZE = 10
        FRAME_PUBLISH_TIMER_PERIOD_SECONDS = 0.1

        # Maybe not needed, but figured it would be good to have a separate timer for tag detection
        # since it is a more expensive operation than just publishing the camera frame.
        TAG_DETECTION_TIMER_PERIOD_SECONDS = 0.5

        super().__init__("camera_node")
        self.get_logger().info(colorStr("Launching Camera Node", ColorCodes.GREEN_OK))

        self._publisher = self.create_publisher(CompressedImage, topicName, PUBLISHER_QUEUE_SIZE)
        self.get_logger().info(colorStr(f"Created Publisher: {topicName}", ColorCodes.GREEN_OK))

        self.frameTimer = self.create_timer(FRAME_PUBLISH_TIMER_PERIOD_SECONDS, self.publishFrame)
        self.tagTimer = self.create_timer(TAG_DETECTION_TIMER_PERIOD_SECONDS, self.detectTags)

        self.frameCapture = cv.VideoCapture(camera)
        self.bridge = CvBridge()

        self.declare_parameter("camera_id", camera)

    def _publishCameraFrame(self) -> None:
        """
        Callback function to publish a camera frame to the specified topic.
        """

        ret, frame = self.frameCapture.read()

        if ret:
            self._publisher.publish(self.bridge.cv2_to_compressed_imgmsg(frame))

    def _detectTags(self) -> None:
        """
        Callback function to detect tags in the camera frame.
        """

        # TODO implement

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

