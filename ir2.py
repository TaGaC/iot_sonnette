import RPi.GPIO as GPIO
import time

# --- Définition des pins ---
TOUCH_PIN = 17   # Capteur tactile DFR0030
PIR_PIN = 23     # Capteur PIR SEN0018
SPEAKER_PIN = 18 # Haut-parleur

# --- Setup GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)

# --- PWM pour le haut-parleur ---
pwm = GPIO.PWM(SPEAKER_PIN, 1000)

def play_bip(duration=0.5):
    pwm.start(50)
    time.sleep(duration)
    pwm.stop()

# --- Anti-spam PIR ---
last_pir_trigger = 0
COOLDOWN = 2  # secondes

# --- Délai d'initialisation PIR ---
print("⏳ Initialisation du capteur PIR (10s)... Ne bouge pas devant !")
time.sleep(2)
print("✅ PIR activé. Prêt à détecter les mouvements.")

try:
    while True:
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            print("🖐️ Appui tactile détecté !")
            play_bip()

        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            now = time.time()
            if now - last_pir_trigger > COOLDOWN:
                print("🕴️ Mouvement détecté par PIR !")
                play_bip()
                last_pir_trigger = now

        time.sleep(0.1)

except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()
