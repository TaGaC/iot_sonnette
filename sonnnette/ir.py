import RPi.GPIO as GPIO
import time

# --- Définition des pins ---
TOUCH_PIN = 17   # GPIO17 (DFR0030)
PIR_PIN = 23     # GPIO23 (SEN0018)
SPEAKER_PIN = 18 # GPIO18 (PWM)

# --- Setup GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)

# --- PWM pour le haut-parleur ---
pwm = GPIO.PWM(SPEAKER_PIN, 1000)  # Fréquence de 1kHz

def play_bip(duration=0.5):
    pwm.start(50)  # 50% duty cycle
    time.sleep(duration)
    pwm.stop()

print("Capteur prêt : Appuie ou détecte un mouvement pour déclencher le son.")

try:
    while True:
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            print("Appui tactile détecté !")
            play_bip()

        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            print("Mouvement détecté par PIR !")
            play_bip()

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Arrêt du script.")

finally:
    pwm.stop()
    GPIO.cleanup()

