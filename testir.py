import RPi.GPIO as GPIO
import time

IR_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

try:
    while True:
        print("IR_PIN =", GPIO.input(IR_PIN))
        time.sleep(0.5)
except KeyboardInterrupt:
    GPIO.cleanup()
