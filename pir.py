import RPi.GPIO as GPIO
import time

IR_PIN = 14      # BCM pour SEN0018 OUT
CALIB_TIME = 10  # warm-up en secondes

GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print(f"Warm-up du capteur PIR/IR pendant {CALIB_TIME}s… ne bougez pas devant.")
time.sleep(CALIB_TIME)

print(" Capteur stabilisé. Démarrage de la lecture :\n")
try:
    while True:
        if GPIO.input(IR_PIN) == GPIO.HIGH:
            print(" MOUVEMENT détecté !")
        else:
            print("⏸ Pas de mouvement.")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\n Arrêt, nettoyage des GPIO.")
    GPIO.cleanup()
