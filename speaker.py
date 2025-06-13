import RPi.GPIO as GPIO
import time

# --- Configuration de base ---
GPIO.setmode(GPIO.BCM)
SPEAKER_PIN = 18  # GPIO18 recommandé pour le PWM

GPIO.setup(SPEAKER_PIN, GPIO.OUT)

# --- Créer un signal PWM sur la pin ---
pwm = GPIO.PWM(SPEAKER_PIN, 1)  # Fréquence initiale à 1 Hz (sera changée)

try:
    print("Test du haut-parleur (alimentation 3.3V)")
    for freq in [440, 660, 880, 1000]:  # Fréquences en Hz (La, Mi, La+, 1kHz)
        print(f"Joue {freq} Hz")
        pwm.ChangeFrequency(freq)
        pwm.start(50)  # 50% de duty cycle
        time.sleep(0.5)  # Durée du bip
        pwm.stop()
        time.sleep(0.2)  # Pause entre les bips

    print("Fin du test.")
    
finally:
    pwm.stop()
    GPIO.cleanup()

