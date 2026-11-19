from glob import glob

from setuptools import find_packages, setup

package_name = "rover_launch"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TrickFire Robotics",
    maintainer_email="dev@trickfirerobotics.com",
    description="Launch files for the TrickFire URC rover.",
    license="MIT",
    entry_points={
        "console_scripts": [],
    },
)
