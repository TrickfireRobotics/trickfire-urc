import random
from pathlib import Path

import cv2
import pytest
from ar_tag_detection.ar_tag_detection import TagDetectionLogic
from cv_bridge import CvBridge

wanted_tag_type = cv2.aruco.DICT_4X4_50
unit_under_test = TagDetectionLogic(wanted_tag_type)


def generate_4x4_50_test_markers(
    output_dir: Path, amount: int = 5, marker_size: int = 200, sequential_ids: bool = True
) -> list:
    """Generates ArUco marker images into a target directory with unique IDs."""
    output_dir.mkdir(exist_ok=True, parents=True)

    if sequential_ids:
        generated_ids = list(range(amount))
    else:
        # DICT_4X4_50 has 50 valid IDs (0 through 49)
        generated_ids = random.sample(range(50), amount)

    for marker_id in generated_ids:
        marker_image = cv2.aruco.generateImageMarker(
            cv2.aruco.getPredefinedDictionary(wanted_tag_type), marker_id, marker_size
        )

        margin = 20
        marker_image = cv2.copyMakeBorder(
            marker_image, margin, margin, margin, margin, cv2.BORDER_CONSTANT, value=255
        )

        cv2.imwrite(str(output_dir / f"marker_{marker_id}.png"), marker_image)

    return generated_ids


def test_draw_detected_markers(tmp_path: Path) -> None:
    test_images: Path = tmp_path / "test_images"
    output_dir: Path = tmp_path / "output_images"
    output_dir.mkdir()

    bridge = CvBridge()

    generated_ids = generate_4x4_50_test_markers(
        amount=50, marker_size=200, sequential_ids=False, output_dir=test_images
    )
    discovered_ids = []
    for file_path in sorted(test_images.iterdir()):
        if file_path.is_file():
            print(f"Testing Image: {file_path.name}")

            cv_image = cv2.imread(str(file_path))
            msg = bridge.cv2_to_compressed_imgmsg(cv_image)

            (frame, ids, _) = unit_under_test.feedFrame(msg)

            discovered_ids.extend(ids.data)
            uncompressed_frame = bridge.compressed_imgmsg_to_cv2(frame, desired_encoding="bgr8")

            output_path = output_dir / f"annotated_{file_path.name}"
            cv2.imwrite(str(output_path), uncompressed_frame)

    assert sorted(discovered_ids) == sorted(generated_ids)
