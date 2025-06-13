import RPi.GPIO as GPIO
import time

# Broche BCM connectée à la sortie OUT du capteur IR
IR_PIN = 23

# Intervalle entre deux lectures (en secondes)
INTERVAL = 0.1

# --- Configuration GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("Lecture brute du capteur IR (1 = mouvement / 0 = pas de mouvement).")
print("Appuyez sur Ctrl+C pour arrêter.\n")

try:
    while True:
        state = GPIO.input(IR_PIN)
        print(state)
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nArrêt, GPIO nettoyés.")
