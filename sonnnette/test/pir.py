import RPi.GPIO as GPIO
import time

IR_PIN = 23    # BCM pour la sortie du capteur
GPIO.setmode(GPIO.BCM)
# On s’appuie sur le pull-down interne
GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def ir_detecte(tries=3, delay=0.03):
    """
    Lit IR_PIN 'tries' fois, avec 'delay' secondes entre chaque.
    Ne renvoie True (mouvement) que si toutes les lectures sont à 1.
    """
    for _ in range(tries):
        if GPIO.input(IR_PIN) == GPIO.LOW:
            return False
        time.sleep(delay)
    return True

# Warm-up
print("?? Warm-up du capteur (30 s)… ne bougez pas devant.")
time.sleep(30)

print("? Démarrage du test IR filtré :")
try:
    while True:
        if ir_detecte():
            print("?? Mouvement détecté")
            # ici tu joues ton bip ou déclenches ton action
            time.sleep(2)  # anti-spam
        else:
            print("??  Pas de mouvement")
        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
