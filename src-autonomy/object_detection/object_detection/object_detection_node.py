import os

import cv2
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image
from ultralytics import YOLO
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose


class ObjectDetectionNode(Node):
    def __init__(self):
        super().__init__("object_detection")
        # declare parameters

        # self.declare_parameter("image_topic", "/image_raw")
        self.declare_parameter("image_topic", "/zed/zed_node/rgb/color/rect/image")
        self.declare_parameter("detections_topic", "/detections")
        self.declare_parameter("annotated_image_topic", "/image_annotated")
        self.declare_parameter("model_name", "yolo26n.pt")
        self.declare_parameter("model_task", "detect")

        # Get parameters
        image_topic: str = str(self.get_parameter("image_topic").value)
        detections_topic: str = str(self.get_parameter("detections_topic").value)
        model_name: str = str(self.get_parameter("model_name").value)
        annotated_image_topic: str = str(self.get_parameter("annotated_image_topic").value)
        model_task: str = str(self.get_parameter("model_task").value)

        # Initialize CV Bridge
        self.bridge = CvBridge()

        self.get_logger().info(f"Loading YOLO model")
        self.model = YOLO(model=str(model_name), task=str(model_task), verbose=True)
        self.get_logger().info("YOLO model loaded successfully")

        # Create subscriber and publishers
        self.img_sub = self.create_subscription(Image, image_topic, self.image_callback, 10)
        self.det_pub = self.create_publisher(Detection2DArray, detections_topic, 10)
        self.annotated_img_pub = self.create_publisher(Image, annotated_image_topic, 10)
        self.compressed_img_pub = self.create_publisher(
            CompressedImage, annotated_image_topic + "/compressed", 10
        )

        self.get_logger().info(f"Subscribing to: {image_topic}")
        self.get_logger().info(f"Publishing detections to: {detections_topic}")

        self.camera_subscriber = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            qos_profile_sensor_data,
        )
        self.detection_pub = self.create_publisher(Detection2DArray, "detections", 10)

    def image_callback(self, msg):
        try:
            # Convert ROS Image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            # Run YOLO detection
            results = self.model(cv_image, verbose=False)

            # Create Detection2DArray message
            detection_array = Detection2DArray()
            detection_array.header = msg.header

            # Process each detection
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    detection = Detection2D()

                    # Get bounding box coordinates (xyxy format)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    # Set bounding box center and size
                    detection.bbox.center.position.x = float((x1 + x2) / 2)
                    detection.bbox.center.position.y = float((y1 + y2) / 2)
                    detection.bbox.size_x = float(x2 - x1)
                    detection.bbox.size_y = float(y2 - y1)

                    # Draw bounding box onto image
                    x1 = int(x1)
                    y1 = int(y1)
                    x2 = int(x2)
                    y2 = int(y2)
                    cv2.rectangle(cv_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    label = int(box.cls[0])
                    label_readable = self.model.names[label]
                    score = float(box.conf[0])

                    # Set detection hypothesis (class and confidence)
                    hypothesis = ObjectHypothesisWithPose()
                    hypothesis.hypothesis.class_id = str(label)
                    hypothesis.hypothesis.score = score

                    text = f"{label_readable}: {score:.2f}"
                    cv2.putText(
                        cv_image,
                        text,
                        (x1, max(y1 - 5, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                        cv2.LINE_AA,
                    )

                    detection.results.append(hypothesis)
                    detection_array.detections.append(detection)

            # Publish detections and annotated images
            self.detection_pub.publish(detection_array)

            annotated_img_msg = self.bridge.cv2_to_imgmsg(cv_image, encoding="bgr8")
            annotated_img_msg.header = msg.header
            self.annotated_img_pub.publish(annotated_img_msg)

            compressed_image_msg = CompressedImage()
            compressed_image_msg.header = msg.header
            compressed_image_msg.format = "jpeg"
            compressed_image_msg.data = np.array(cv2.imencode(".jpg", cv_image)[1]).tobytes()
            self.compressed_img_pub.publish(compressed_image_msg)

            self.get_logger().debug(f"Published {len(detection_array.detections)} detections")

        except Exception as e:
            self.get_logger().error(f"Error processing image: {str(e)}")


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
