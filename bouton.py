import RPi.GPIO as GPIO
import time

# --- Pins utilisés ---
TOUCH_PIN = 17  # GPIO17 = Pin 11
SPEAKER_PIN = 18  # GPIO18 = Pin 12

# --- Setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)

pwm = GPIO.PWM(SPEAKER_PIN, 1000)  # 1 kHz

print("Appuie sur le capteur tactile pour déclencher la sonnerie (CTRL+C pour quitter)")

try:
    while True:
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            print("TOUCH détecté ! Sonnerie...")
            pwm.start(50)
            time.sleep(0.5)
            pwm.stop()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Arrêt demandé.")

finally:
    pwm.stop()
    GPIO.cleanup()
