import Jetson.GPIO as GPIO
import rclpy
from hall_effect_sensor import HallEffectSensor
from limit_switch import LimitSwitch
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.node import Node
from std_msgs.msg import Float32

PIN_NUMBER = 15
HALL_EFFECT_SENSOR_PIN = 18  # Hopefully this is a pin that supports input. If not change it.
HALL_EFFECT_SENSOR_PERIOD = 10  # in milliseconds


class Arm(Node):
    def __init__(self, logger: RcutilsLogger | None = None):
        self.limit_switch = LimitSwitch(PIN_NUMBER)

        GPIO.setmode(GPIO.BOARD)
        super.__init__("ArmNode")
        self._logger: RcutilsLogger = logger or rclpy.logging.get_logger("arm_platform_logger")
        self._check_shoulder_limit_switch_subscriber = self.create_subscription(
            Float32, "shoulder_up", self.check_shoulder_limit_switch, 10
        )

        # self.hall_effect_sensor will get called only when GPIO pin goes low
        self.hall_effect_sensor = HallEffectSensor(
            HALL_EFFECT_SENSOR_PIN, self.hall_effect_sensor_callback, 10
        )

        # For now timing is used to calculated rotation in order to keep track of magnet gap.
        # TODO figure out how to calculate the rotation based on magnet gap.
        self.initial_time = self.get_clock().now()

    def check_shoulder_limit_switch(self):
        pressed = self.limit_switch.is_pressed()
        self._logger.log("shoulder is pressed" + pressed)

    def hall_effect_sensor_callback(self):
        self.get_logger().info("Magnet was passed.")
        self.initial_time = self.get_clock().now()


def main():
    rclpy.init()
    arm_node = Arm()
    try:
        rclpy.spin(arm_node)
    except KeyboardInterrupt:
        pass
    finally:
        arm_node.destroy_node()
        GPIO.cleanup()
        rclpy.shutdown()
