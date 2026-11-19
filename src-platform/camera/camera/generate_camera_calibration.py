# standalone script, not a ROS node - run manually against a folder of checkerboard photos

import glob
import json
import os

import cv2 as cv
import numpy as np

# ---------------------------------------------------------------------------- #
#                                    Config                                    #
# ---------------------------------------------------------------------------- #

BOARD_WIDTH_SQUARES = 9
BOARD_HEIGHT_SQUARES = 7
CHECKERBOARD = (BOARD_WIDTH_SQUARES - 1, BOARD_HEIGHT_SQUARES - 1)  # inner corners, not squares

CORNER_SUBPIX_WINDOW = (11, 11)
CORNER_SUBPIX_CRITERIA = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(SCRIPT_DIR, "calibration_images")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "camera_calibration.json")

# ---------------------------------------------------------------------------- #
#                                 Calibration                                  #
# ---------------------------------------------------------------------------- #


def generate_camera_calibration_file() -> None:
    """Finds checkerboard corners in calibration_images/*.jpg and writes calibration data out"""
    images = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
    if not images:
        print(f"Error: no calibration images found in {IMAGE_DIR}")
        return

    object_points, image_points, image_size = _find_checkerboard_corners(images)
    if not object_points:
        print("Error: checkerboard corners could not be found in any of the images.")
        return

    ok, camera_matrix, dist_coeffs, _, _ = cv.calibrateCamera(
        object_points, image_points, image_size, None, None
    )
    if not ok:
        print("Error: camera calibration failed.")
        return

    calibration_data = {
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.tolist(),
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(calibration_data, f, indent=4)

    print(f"Camera calibration data successfully saved to {OUTPUT_PATH}")


# ---------------------------------------------------------------------------- #
#                                  Internals                                   #
# ---------------------------------------------------------------------------- #


def _find_checkerboard_corners(
    image_paths: list[str],
) -> tuple[list[np.ndarray], list[np.ndarray], tuple[int, int] | None]:
    """Reads each image and, where a checkerboard is visible, records its corner points"""
    board_points = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    board_points[:, :2] = np.mgrid[0 : CHECKERBOARD[1], 0 : CHECKERBOARD[0]].T.reshape(-1, 2)

    object_points = []  # 3D board points, repeated once per image where the board was found
    image_points = []  # 2D corner points, one set per image
    image_size = None

    for path in image_paths:
        img = cv.imread(path)
        if img is None:
            print(f"Warning: could not read image {path}")
            continue

        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        image_size = gray.shape[::-1]

        found, corners = cv.findChessboardCorners(gray, CHECKERBOARD, None)
        if not found:
            print(f"Warning: checkerboard corners not found in {os.path.basename(path)}")
            continue

        object_points.append(board_points)
        image_points.append(
            cv.cornerSubPix(gray, corners, CORNER_SUBPIX_WINDOW, (-1, -1), CORNER_SUBPIX_CRITERIA)
        )

    return object_points, image_points, image_size


if __name__ == "__main__":
    generate_camera_calibration_file()
