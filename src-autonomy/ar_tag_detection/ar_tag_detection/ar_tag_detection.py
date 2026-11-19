import argparse
import sys

import cv2 as cv
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Pose, PoseArray
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Int32MultiArray

Point2D = tuple[int, int]

# ---------------------------------------------------------------------------- #
#                                    Config                                    #
# ---------------------------------------------------------------------------- #

TAG_DICTIONARY = cv.aruco.DICT_4X4_50
MARKER_SIZE_M = 0.05

DEFAULT_IMAGE_TOPIC = "/zed/zed_node/rgb/color/rect/image"
DEFAULT_CAMERA_INFO_TOPIC = "/zed/zed_node/rgb/color/rect/camera_info"
DEFAULT_PROCESS_RATE_HZ = 2.0

QUEUE_SIZE = 10

# ---------------------------------------------------------------------------- #
#                             Tag Detection Logic                              #
# ---------------------------------------------------------------------------- #


class TagDetectionLogic:
    """Processes image frames to identify and draw ArUco fiducial markers"""

    def __init__(
        self,
        wanted_tag_type: int,
        marker_size: float = MARKER_SIZE_M,
        camera_matrix: np.ndarray | None = None,
        dist_coeffs: np.ndarray | None = None,
        logger: RcutilsLogger | None = None,
    ) -> None:
        self._detected_tag_type = cv.aruco.getPredefinedDictionary(wanted_tag_type)

        # fall back for OpenCV < 4.7, which doesn't have ArucoDetector yet
        has_new_api = hasattr(cv.aruco, "ArucoDetector")
        self._detected_tag_params = (
            cv.aruco.DetectorParameters() if has_new_api else cv.aruco.DetectorParameters_create()
        )
        self._detector = (
            cv.aruco.ArucoDetector(self._detected_tag_type, self._detected_tag_params)
            if has_new_api
            else None
        )

        self.bridge = CvBridge()
        self._logger = logger or rclpy.logging.get_logger("tag_detection_logic")
        self._marker_size = marker_size
        self._camera_matrix = camera_matrix
        self._dist_coeffs = dist_coeffs
        self.marker_points = _marker_corner_points(marker_size)

    @property
    def is_calibrated(self) -> bool:
        """Returns True if valid camera calibration data has been set"""
        return self._camera_matrix is not None and self._dist_coeffs is not None

    def update_camera_info(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray) -> None:
        """Updates internal camera intrinsic matrix and distortion coefficients"""
        self._camera_matrix = camera_matrix
        self._dist_coeffs = dist_coeffs

    def feed_frame(
        self, frame: Image
    ) -> tuple[Image, Int32MultiArray, Int32MultiArray, list[Pose]]:
        """Detects ArUco tags in the given frame and returns an annotated copy plus their data"""
        converted_frame = self.bridge.imgmsg_to_cv2(frame, desired_encoding="bgr8")

        if self._detector is not None:
            corners, ids, _ = self._detector.detectMarkers(converted_frame)
        else:
            corners, ids, _ = cv.aruco.detectMarkers(
                converted_frame, self._detected_tag_type, parameters=self._detected_tag_params
            )

        detected_ids = Int32MultiArray(data=[])
        detected_corners = Int32MultiArray(data=[])
        pose_list: list[Pose] = []

        if ids is not None and len(corners) > 0:
            cv.aruco.drawDetectedMarkers(converted_frame, corners, ids)

            for marker_corners, marker_id in zip(corners, ids.flatten()):
                tl, tr, br, bl = _corners_to_points(marker_corners)
                detected_ids.data.append(int(marker_id))
                detected_corners.data.extend([*tl, *tr, *br, *bl])

                pose = self._solve_pose(converted_frame, marker_corners)
                if pose is not None:
                    pose_list.append(pose)

        annotated_image = self.bridge.cv2_to_imgmsg(converted_frame, encoding="bgr8")
        return annotated_image, detected_ids, detected_corners, pose_list

    # ------------------------------------------------------------------------ #
    #                                 Internals                                #
    # ------------------------------------------------------------------------ #

    def _solve_pose(self, frame: np.ndarray, marker_corners: np.ndarray) -> Pose | None:
        """Solves for a marker's 3D pose and draws its axes onto the frame, if calibrated"""
        if not self.is_calibrated:
            return None

        success, rvec, tvec = cv.solvePnP(
            self.marker_points, marker_corners, self._camera_matrix, self._dist_coeffs
        )
        if not success:
            return None

        rot_matrix, _ = cv.Rodrigues(rvec)
        qx, qy, qz, qw = _rotation_matrix_to_quaternion(rot_matrix)

        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = (float(v) for v in tvec[:, 0])
        pose.orientation.x = qx
        pose.orientation.y = qy
        pose.orientation.z = qz
        pose.orientation.w = qw

        cv.drawFrameAxes(
            frame, self._camera_matrix, self._dist_coeffs, rvec, tvec, self._marker_size
        )
        return pose


def _marker_corner_points(marker_size: float) -> np.ndarray:
    """Builds the 3D corner points of a flat square marker, centered on the origin"""
    half = marker_size / 2.0
    return np.array(
        [[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]],
        dtype=np.float32,
    )


def _corners_to_points(corners: np.ndarray) -> tuple[Point2D, Point2D, Point2D, Point2D]:
    """Converts a detected tag's corner array into integer (x, y) coordinate tuples"""
    top_left, top_right, bottom_right, bottom_left = corners.reshape((4, 2))
    return tuple((int(x), int(y)) for x, y in (top_left, top_right, bottom_right, bottom_left))


def _rotation_matrix_to_quaternion(matrix: np.ndarray) -> np.ndarray:
    """Converts a 3x3 rotation matrix into a [qx, qy, qz, qw] unit quaternion"""
    m00, m01, m02 = matrix[0]
    m10, m11, m12 = matrix[1]
    m20, m21, m22 = matrix[2]

    trace = m00 + m11 + m22

    if trace > 0:
        scale_factor = np.sqrt(trace + 1.0) * 2
        qw = 0.25 * scale_factor
        qx = (m21 - m12) / scale_factor
        qy = (m02 - m20) / scale_factor
        qz = (m10 - m01) / scale_factor
    elif (m00 > m11) and (m00 > m22):
        scale_factor = np.sqrt(1.0 + m00 - m11 - m22) * 2
        qw = (m21 - m12) / scale_factor
        qx = 0.25 * scale_factor
        qy = (m01 + m10) / scale_factor
        qz = (m02 + m20) / scale_factor
    elif m11 > m22:
        scale_factor = np.sqrt(1.0 + m11 - m00 - m22) * 2
        qw = (m02 - m20) / scale_factor
        qx = (m01 + m10) / scale_factor
        qy = 0.25 * scale_factor
        qz = (m12 + m21) / scale_factor
    else:
        scale_factor = np.sqrt(1.0 + m22 - m00 - m11) * 2
        qw = (m10 - m01) / scale_factor
        qx = (m02 + m20) / scale_factor
        qy = (m12 + m21) / scale_factor
        qz = 0.25 * scale_factor

    return np.array([qx, qy, qz, qw])


# ---------------------------------------------------------------------------- #
#                                   ROS Node                                   #
# ---------------------------------------------------------------------------- #


class ArTagDetectionNode(Node):
    """ROS 2 node that detects ArUco tags in a camera feed and publishes their ids/corners/poses"""

    def __init__(self, camera_id: int = 0) -> None:
        super().__init__(f"ar_tag_detection_node_{camera_id}")

        self.declare_parameter("image_topic", DEFAULT_IMAGE_TOPIC)
        self.declare_parameter("image_calibration_topic", DEFAULT_CAMERA_INFO_TOPIC)
        self.declare_parameter("process_rate_hz", DEFAULT_PROCESS_RATE_HZ)

        image_topic = self.get_parameter("image_topic").value
        image_calibration_topic = self.get_parameter("image_calibration_topic").value
        process_rate_hz = self.get_parameter("process_rate_hz").value

        self._min_process_interval = 1.0 / process_rate_hz if process_rate_hz > 0 else 0.0
        self._last_process_time = self.get_clock().now()
        self._tag_detection_logic = TagDetectionLogic(
            wanted_tag_type=TAG_DICTIONARY, logger=self.get_logger()
        )

        self.tag_detection_topic = f"/camera_{camera_id}/tags"
        self.tag_id_topic = f"/camera_{camera_id}/tags/ids"
        self.tag_corners_topic = f"/camera_{camera_id}/tags/tag_corners"
        self.tag_poses_topic = f"/camera_{camera_id}/tags/tag_poses"

        self._camera_subscriber = self.create_subscription(
            Image, image_topic, self._on_frame, QUEUE_SIZE
        )
        self._camera_info_subscriber = self.create_subscription(
            CameraInfo, image_calibration_topic, self._on_camera_info, QUEUE_SIZE
        )
        self._tag_publisher = self.create_publisher(Image, self.tag_detection_topic, QUEUE_SIZE)
        self._tag_id_publisher = self.create_publisher(
            Int32MultiArray, self.tag_id_topic, QUEUE_SIZE
        )
        self._tag_corners_publisher = self.create_publisher(
            Int32MultiArray, self.tag_corners_topic, QUEUE_SIZE
        )
        self._tag_poses_publisher = self.create_publisher(
            PoseArray, self.tag_poses_topic, QUEUE_SIZE
        )

        self.get_logger().info(f"ar_tag_detection_node subscribed to {image_topic}")

    # ---------------------------------------------------------------------------- #
    #                                  Internals                                   #
    # ---------------------------------------------------------------------------- #

    def _on_camera_info(self, msg: CameraInfo) -> None:
        """Applies camera calibration, then unsubscribes since it won't change again"""
        camera_matrix = np.array(msg.k, dtype=np.float64).reshape((3, 3))
        dist_coeffs = np.array(msg.d, dtype=np.float64)

        self._tag_detection_logic.update_camera_info(camera_matrix, dist_coeffs)
        self.get_logger().info("Received and applied camera calibration parameters")
        self.destroy_subscription(self._camera_info_subscriber)

    def _on_frame(self, msg: Image) -> None:
        """Rate-limits incoming frames and forwards the rest to the detection logic"""
        now = self.get_clock().now()
        if (now - self._last_process_time).nanoseconds / 1e9 < self._min_process_interval:
            return
        self._last_process_time = now

        frame, ids_msg, corners_msg, pose_list = self._tag_detection_logic.feed_frame(msg)

        optical_frame_id = msg.header.frame_id or "ar_tag_detection_optical_frame"
        frame.header.stamp = now.to_msg()
        frame.header.frame_id = optical_frame_id

        self._tag_publisher.publish(frame)
        self._tag_id_publisher.publish(ids_msg)
        self._tag_corners_publisher.publish(corners_msg)

        poses_msg = PoseArray()
        poses_msg.header.stamp = now.to_msg()
        poses_msg.header.frame_id = optical_frame_id
        poses_msg.poses = pose_list
        self._tag_poses_publisher.publish(poses_msg)


# ---------------------------------------------------------------------------- #
#                                  Entrypoint                                  #
# ---------------------------------------------------------------------------- #


def _parse_camera_id(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--camera-id", type=int, default=0)
    parsed, _ = parser.parse_known_args(argv)
    return parsed.camera_id


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)

    camera_id = _parse_camera_id(sys.argv if args is None else args)
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
