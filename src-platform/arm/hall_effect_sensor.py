import Jetson.GPIO as GPIO

#TODO look into event detects with bouncetime
#TODO figure out how 3 magnets can be used to calculate rotation in main arm node
#TODO figure out how to configure it physically so that all the timing matches.


class HallEffectSensor:

    def __init__(self,pin, event_callback, debounce=10):
        self._pin = pin
        if GPIO.getmode() is None: # idk why this is there but its there
            GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Pulled up. when magnet goes over
        #sensor, GPIO pin gets pulled down.

        GPIO.add_event_detect(self._pin, GPIO.FALLING, callback=event_callback, bouncetime=debounce)

        # look into using an event with bouncetime

