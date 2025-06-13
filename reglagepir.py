import RPi.GPIO as GPIO
import time

# BCM pin pour la sortie du capteur IR
IR_PIN = 23

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Warm-up du capteur
CALIB_TIME = 5
print(f" Warm-up du capteur IR pendant {CALIB_TIME}s… ne bougez pas devant.")
time.sleep(CALIB_TIME)

print(" Capteur stabilisé. Surveillance des changements d’état (Ctrl+C pour arrêter) …")

# Lecture initiale
prev_state = GPIO.input(IR_PIN)
last_time = time.time()

try:
    while True:
        current = GPIO.input(IR_PIN)
        if current != prev_state:
            now = time.time()
            duration = now - last_time
            state_str = "HIGH" if prev_state == GPIO.HIGH else "LOW"
            print(f"{state_str} a duré {duration:.3f} s")
            prev_state = current
            last_time = now
        time.sleep(0.01)  # 10 ms entre chaque vérif
except KeyboardInterrupt:
    GPIO.cleanup()
    print("\n Arrêt, nettoyage des GPIO.")
