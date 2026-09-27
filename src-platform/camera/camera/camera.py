import threading

import cv2 as cv
import rclpy
from cv2.typing import MatLike
from cv_bridge import CvBridge
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage


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
            is_reading, _ = camera.read()
            _ = camera.get(WIDTH_PROPERTY_ID)
            _ = camera.get(HEIGHT_PROPERTY_ID)
            if is_reading:
                working_ports.append(dev_port)
            camera.release()
        dev_port += 1

    return working_ports


class CameraNode(Node):
    """A node for handling camera operations."""

    def __init__(self, topicName: str, camera: int) -> None:

        PUBLISHER_QUEUE_SIZE = 10
        FRAME_PUBLISH_TIMER_PERIOD_SECONDS = 0.1

        self.FRAME_PUBLISHER_TOPIC = f"{topicName}/raw"

        super().__init__(f"camera_node_{camera}")

        self.get_logger().info(f"Launching Camera Node: {camera}")

        self._framePublisher = self.create_publisher(
            CompressedImage, self.FRAME_PUBLISHER_TOPIC, PUBLISHER_QUEUE_SIZE
        )

        self.frameTimer = self.create_timer(
            FRAME_PUBLISH_TIMER_PERIOD_SECONDS, self._publishCameraFrame
        )

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
