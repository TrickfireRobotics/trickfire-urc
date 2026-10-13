source /opt/ros/$ROS_DISTRO/setup.bash
#sudo apt-get update
#sudo rosdep init
#rosdep update
#rosdep install --from-paths ~/trickfire-urc --ignore-src -r -y
colcon build --symlink-install --packages-up-to ublox
