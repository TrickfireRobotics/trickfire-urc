"""
This module provides functionality to generate camera calibration data using OpenCV's
camera calibration functions and save the calibration data to a JSON file for later use.

Note: this shouldnt be ran on the robot during normal operation, hence no ROS node creation
"""

import glob
import json
import os

import cv2 as cv
import numpy as np


def generate_camera_calibration_file() -> None:
    """
    Generates camera calibration data from images of a checkerboard pattern and saves it to a JSON
    file.
    """
    BOARD_WIDTH_SQUARES = 9
    BOARD_HEIGHT_SQUARES = 7

    CHECKERBOARD = (BOARD_WIDTH_SQUARES - 1, BOARD_HEIGHT_SQUARES - 1)

    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0 : CHECKERBOARD[1], 0 : CHECKERBOARD[0]].T.reshape(-1, 2)

    objpoints = []  # 3D points in real world space
    imgpoints = []  # 2D points in image plane

    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_pattern = os.path.join(script_dir, "calibration_images", "*.jpg")
    images = glob.glob(image_pattern)

    if not images:
        print(
            "Error: No calibration images found in:"
            f"{os.path.join(script_dir, 'calibration_images')}"
        )
        return

    gray_shape = None

    for frame in images:
        img = cv.imread(frame)
        if img is None:
            print(f"Warning: Could not read image {frame}")
            continue

        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        gray_shape = gray.shape[::-1]

        ret, corners = cv.findChessboardCorners(gray, CHECKERBOARD, None)

        if ret:
            objpoints.append(objp)
            corners2 = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            imgpoints.append(corners2)
        else:
            print(f"Warning: Checkerboard corners not found in {os.path.basename(frame)}")

    if not objpoints:
        print("Error: Checkerboard corners could not be found in any of the images.")
        return

    ret, camera_matrix, dist_coeffs, _, _ = cv.calibrateCamera(
        objpoints, imgpoints, gray_shape, None, None
    )

    if ret:
        calibration_data = {
            "camera_matrix": camera_matrix.tolist(),
            "dist_coeffs": dist_coeffs.tolist(),
        }

        output_path = os.path.join(script_dir, "camera_calibration.json")
        with open(output_path, "w") as f:
            json.dump(calibration_data, f, indent=4)

        print(f"Camera calibration data successfully saved to {output_path}")
    else:
        print("Error: Camera calibration failed.")


if __name__ == "__main__":
    generate_camera_calibration_file()
