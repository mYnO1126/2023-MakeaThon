import RPi.GPIO as GPIO
import time
import SmartFarmControl

control=SmartFarmControl.SmartFarmControl()
#control.test()
control.initializing_end_to_end()
