import Jetson.GPIO as GPIO
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

PIN_NUMBER = None  # TODO: set the pin number


class LimitSwitch(Node):
    def __init__(self):
        super().__init__("limit_switch_node")
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(PIN_NUMBER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._publisher = self.create_publisher(Bool, "limit_switch_publisher", 10)
        self._timer = self.create_timer(0.5, self.timer_callback)
        self._last_state = None

    def timer_callback(self):
        pressed = GPIO.input(PIN_NUMBER) == GPIO.LOW

        if self._last_state is not None and pressed == self._last_state:
            return

        pub_data = Bool()
        self._last_state = pressed
        pub_data.data = pressed
        self._publisher.publish(pub_data)


def main():
    rclpy.init()
    limit_switch_node = LimitSwitch()
    try:
        rclpy.spin(limit_switch_node)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
        limit_switch_node.destroy_node()
        rclpy.shutdown()
