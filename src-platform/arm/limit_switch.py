import Jetson.GPIO as GPIO


class LimitSwitch:
    def __init__(self, pin: int):
        self._pin = pin
        if GPIO.getmode() is None:
            GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def is_pressed(self) -> bool:
        # LOW means the switch is pressed
        return GPIO.input(self._pin) == GPIO.LOW
