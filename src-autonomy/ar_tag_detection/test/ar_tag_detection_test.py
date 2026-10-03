from pathlib import Path

import cv2
import pytest
from ar_tag_detection.ar_tag_detection import TagDetectionLogic
from cv_bridge import CvBridge

unit_under_test = TagDetectionLogic(cv2.aruco.DICT_4X4_50)


def test_draw_detected_markers():
    test_images: Path = Path(__file__).parent / "test_images"
    output_dir: Path = Path(__file__).parent / "output_images"
    output_dir.mkdir(exist_ok=True)

    bridge = CvBridge()

    for file_path in test_images.iterdir():
        if file_path.is_file():
            print(f"Testing Image: {file_path.name}")

            cv_image = cv2.imread(str(file_path))
            msg = bridge.cv2_to_compressed_imgmsg(cv_image)

            (frame, _, _) = unit_under_test.feedFrame(msg)

            uncompressed_frame = bridge.compressed_imgmsg_to_cv2(frame, desired_encoding="bgr8")

            output_path = output_dir / f"annotated_{file_path.name}"
            cv2.imwrite(str(output_path), uncompressed_frame)

    assert True
