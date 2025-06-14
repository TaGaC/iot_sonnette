import RPi.GPIO as GPIO
import time

PIR_PIN = 20  # Mets ici le bon numéro BCM de ta pin PIR

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

print("Calibration PIR 20s...")
time.sleep(20)
print("Début de la lecture PIR toutes les secondes (Ctrl+C pour stopper)\n")

try:
    while True:
        pir_value = GPIO.input(PIR_PIN)
        print(f"[{time.strftime('%H:%M:%S')}] État PIR : {'HIGH (mouvement)' if pir_value else 'LOW (pas de mouvement)'}")
        time.sleep(1)
except KeyboardInterrupt:
    print("Arrêt demandé, nettoyage GPIO...")
    GPIO.cleanup()