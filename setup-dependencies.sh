#setup script for bare metal

#install zed sdk for camera drivers
wget https://download.stereolabs.com/zedsdk/5.4/l4t39.2/jetsons && \
    chmod +x jetsons && \
    ./jetsons

#install stuff for ublox fp9 gps
#from https://github.com/gokulp01/ros2-ublox-zedf9p
mkdir -p ublox_ws/src
cd ublox_ws/src
git clone https://github.com/gokulp01/ros2-ublox-zedf9p.git
cd ..
colcon build
