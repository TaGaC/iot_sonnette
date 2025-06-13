import RPi.GPIO as GPIO
import time

IR_PIN = 23  # BCM

GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("→ Warm-up 30 s… ne bougez pas devant le capteur.")
time.sleep(30)
print("→ Capteur prêt. En attente de front montant (détection).")

try:
    while True:
        # 1) On attend la détection (passage 0→1)
        GPIO.wait_for_edge(IR_PIN, GPIO.RISING)
        t0 = time.time()
        print(f"🔦 Détection à {time.strftime('%H:%M:%S', time.localtime(t0))}")

        # 2) On attend la fin du pulse (passage 1→0)
        GPIO.wait_for_edge(IR_PIN, GPIO.FALLING)
        duree = time.time() - t0
        print(f"   ↳ Durée du pulse HIGH : {duree:.2f} s\n")

        # 3) Boucle relancée, prêt pour la prochaine détection

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Arrêt, GPIO nettoyés.")
