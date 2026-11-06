import Jetson.GPIO as GPIO
from rclpy.node import Node
from std_msgs.msg import Bool


class LimitSwitch(Node):
    def __init__(self, pin):
        super().__init__("limit_switch_node")
        GPIO.setmode(GPIO.BOARD)
        self._pin = pin
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._publisher = self.create_publisher(Bool, "limit_switch_publisher", 10)
        self._timer = self.create_timer(0.5, self.timer_callback)
        self._last_state = None

    def timer_callback(self):
        pressed = GPIO.input(self._pin) == GPIO.LOW

        if self._last_state is not None and pressed == self._last_state:
            return

        pub_data = Bool()
        self._last_state = pressed
        pub_data.data = pressed
        self._publisher.publish(pub_data)
