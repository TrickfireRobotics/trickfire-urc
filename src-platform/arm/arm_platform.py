import Jetson.GPIO as GPIO
import rclpy
from limit_switch import LimitSwitch
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.node import Node
from std_msgs.msg import Float32

PIN_NUMBER = 15


class Arm(Node):
    def __init__(self, logger: RcutilsLogger | None = None):
        self.limit_switch = LimitSwitch(PIN_NUMBER)
        GPIO.setmode(GPIO.BOARD)
        super.__init__("ArmNode")
        self._logger: RcutilsLogger = logger or rclpy.logging.get_logger("arm_platform_logger")
        self._check_shoulder_limit_switch_subscriber = self.create_subscription(
            Float32, "shoulder_up", self.check_shoulder_limit_switch, 10
        )

    def check_shoulder_limit_switch(self):
        pressed = self.limit_switch.is_pressed()
        self._logger.log("shoulder is pressed" + pressed)


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
