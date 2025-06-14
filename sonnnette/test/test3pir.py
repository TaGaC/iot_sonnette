import RPi.GPIO as GPIO
import time

# --- Configuration ---
IR_PIN = 23  # GPIO BCM pour le capteur PIR/IR (SEN0018)

# --- Setup GPIO ---
GPIO.setmode(GPIO.BCM)
# On active un pull-down interne pour que la broche reste a 0 au repos
GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# --- Delai de calibration (warm-up) ---
CALIBRATION_TIME = 4  # secondes

print("?? Calibration du capteur PIR/IR : ne bougez pas pendant {} secondes...".format(CALIBRATION_TIME))
time.sleep(CALIBRATION_TIME)
print("? Calibration terminee. Lecture du capteur :\n")

try:
    while True:
        val = GPIO.input(IR_PIN)
        if val == GPIO.HIGH:
            print("IR_PIN = 1  (Mouvement detecte)")
        else:
            print("IR_PIN = 0  (Pas de mouvement)")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nArret par l'utilisateur, nettoyage des GPIO...")
    GPIO.cleanup()
