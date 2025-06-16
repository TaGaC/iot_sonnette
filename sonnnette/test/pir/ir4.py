import RPi.GPIO as GPIO
import time

# --- Définition des pins (BCM) ---
TOUCH_PIN = 17    # Capteur tactile DFR0030
IR_PIN    = 23    # Capteur IR SEN0018 (sortie numérique)
SPEAKER_PIN = 18  # Haut-parleur (via PWM)

# --- Configuration GPIO ---
GPIO.setmode(GPIO.BCM)

# Pour les capteurs digitaux, on active une résistance interne de pull-down
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(IR_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(SPEAKER_PIN, GPIO.OUT)

# --- PWM pour le haut-parleur ---
pwm = GPIO.PWM(SPEAKER_PIN, 1000)  # 1 kHz par exemple

def play_bip(duration=0.3):
    """Fait sonner le buzzer pendant duration secondes."""
    pwm.start(50)        # rapport cyclique à 50 %
    time.sleep(duration)
    pwm.stop()

# --- Anti‐spam IR (délai minimal entre deux détections) ---
last_ir_trigger = 0
COOLDOWN = 3.0  # secondes

try:
    print(" Initialisation terminée. En attente d’événements...")
    while True:
        # --- Lecture du bouton tactile ---
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            print(" Appui tactile détecté !")
            play_bip()

            # On peut ajouter un petit délai pour éviter les rebonds
            time.sleep(0.5)

        # --- Lecture du capteur IR ---
        if GPIO.input(IR_PIN) == GPIO.HIGH:
            now = time.time()
            if now - last_ir_trigger > COOLDOWN:
                print("🔦 Détection IR ! Quelqu’un est devant la porte.")
                play_bip(duration=0.5)
                last_ir_trigger = now

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nArrêt par l'utilisateur, nettoyage des GPIO...")
    pwm.stop()
    GPIO.cleanup()
