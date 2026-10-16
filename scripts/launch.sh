source ~/trickfire-urc/install/setup.bash

#important! gps needs to be plugged in, run ls /dev/ttyACM* to check if it shows up
ros2 launch ublox_gps ublox_gps_node-launch.py param_file_name:=zed_f9p
