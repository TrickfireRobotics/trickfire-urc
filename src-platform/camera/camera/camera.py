import threading

import cv2 as cv
import rclpy
from cv_bridge import CvBridge
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

# ---------------------------------------------------------------------------- #
#                                    Config                                    #
# ---------------------------------------------------------------------------- #

QUEUE_SIZE = 10
FRAME_PERIOD_SEC = 0.1  # ~10 fps

# stop probing for camera devices once this many have failed to open
MAX_CLOSED_PORTS = 6

# ---------------------------------------------------------------------------- #
#                               Camera Discovery                               #
# ---------------------------------------------------------------------------- #


def get_available_cameras() -> list[int]:
    """Probes device ports in order and returns the ids of the ones that produce frames"""
    working_ports: list[int] = []
    closed_ports = 0
    dev_port = 0

    # closed_ports is a running total, not a streak, so one bad port early on still
    # counts toward the threshold even if every port after it opens fine
    while closed_ports < MAX_CLOSED_PORTS:
        camera = cv.VideoCapture(dev_port)
        if camera.isOpened():
            is_reading, _ = camera.read()
            if is_reading:
                working_ports.append(dev_port)
            camera.release()
        else:
            closed_ports += 1

        dev_port += 1

    return working_ports


# ---------------------------------------------------------------------------- #
#                                   ROS Node                                   #
# ---------------------------------------------------------------------------- #


class CameraNode(Node):
    """Publishes compressed frames from a single camera device"""

    def __init__(self, topic_name: str, camera_id: int) -> None:
        super().__init__(f"camera_node_{camera_id}")

        self._camera_id = camera_id
        self.declare_parameter("camera_id", camera_id)

        self._capture = cv.VideoCapture(camera_id)
        self._capture_lock = threading.Lock()
        self._bridge = CvBridge()

        self._frame_publisher = self.create_publisher(
            CompressedImage, f"{topic_name}/compressed", QUEUE_SIZE
        )
        self._frame_timer = self.create_timer(FRAME_PERIOD_SEC, self._publish_frame)

        self.get_logger().info(f"camera_node_{camera_id} started, publishing to {topic_name}")

    def destroy_node(self) -> None:
        """Releases the camera device before the node shuts down"""
        if hasattr(self, "_capture") and self._capture.isOpened():
            self._capture.release()
        super().destroy_node()

    # ------------------------------------------------------------------------ #
    #                                 Internals                                #
    # ------------------------------------------------------------------------ #

    def _publish_frame(self) -> None:
        with self._capture_lock:
            got_frame, frame = self._capture.read()

        if not got_frame:
            return

        msg = self._bridge.cv2_to_compressed_imgmsg(frame, dst_format="jpg")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = f"camera_{self._camera_id}_optical_frame"
        self._frame_publisher.publish(msg)


# ---------------------------------------------------------------------------- #
#                                  Entrypoint                                  #
# ---------------------------------------------------------------------------- #


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)

    try:
        nodes = [
            CameraNode(f"/camera_{topic_index}/image", camera_id)
            for topic_index, camera_id in enumerate(get_available_cameras())
        ]

        executor = MultiThreadedExecutor()
        for node in nodes:
            executor.add_node(node)

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
