import RPi.GPIO as GPIO
import time
import requests
from datetime import datetime

# === CONFIGURATION ===
SPEAKER_PIN = 17
TOUCH_PIN = 22
PIR_PIN = 20
COOLDOWN = 4  # anti-spam sonnette
SERVER_URL = "http://145.79.6.244:5000/api/sonnette"
SECRET_KEY = "super_secret"
ALERT_TIMEOUT = 20  # délai avant alerte intrus (secondes)
MIN_HIGH_STREAK = 5    # Nombre de HIGH consécutifs pour valider la présence
MIN_LOW_STREAK = 4     # Nombre de LOW consécutifs pour réarmer

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIR_PIN, GPIO.IN)
pwm = GPIO.PWM(SPEAKER_PIN, 1000)

def play_bip():
    melody = [(523, 0.2), (659, 0.2), (784, 0.2), (1046, 0.3)]
    for freq, dur in melody:
        pwm.ChangeFrequency(freq)
        pwm.start(50)
        time.sleep(dur)
        pwm.stop()
        time.sleep(0.05)

def send_event(evt_type):
    payload = {
        "type": evt_type,
        "timestamp": datetime.utcnow().isoformat(),
        "secret": SECRET_KEY
    }
    try:
        r = requests.post(SERVER_URL, json=payload, timeout=3)
        if r.ok:
            print(f"[{datetime.now().strftime('%H:%M:%S')}]  Événement {evt_type} envoyé.")
        else:
            print(f"[!]  Erreur serveur : {r.status_code}")
    except Exception as e:
        print(f"[!]  Erreur réseau : {e}")

def main_loop():
    print("Calibration du capteur PIR... Merci de ne pas bouger devant le capteur.")
    time.sleep(20)
    print("Calibration terminée. Système prêt. Attente capteur et/ou bouton...")

    last_bell = 0
    high_streak = 0
    low_streak = 0
    intrusion_mode = False
    detection_time = 0
    intrus_sent = False

    try:
        while True:
            now = time.time()
            pir_state = GPIO.input(PIR_PIN) == GPIO.HIGH
            bell_pressed = GPIO.input(TOUCH_PIN) == GPIO.HIGH

            # --- Lecture PIR HIGH/LOW streak ---
            if pir_state:
                high_streak += 1
                low_streak = 0
                restants = MIN_HIGH_STREAK - high_streak
                print(f"[{datetime.now().strftime('%H:%M:%S')}] PIR HIGH ({high_streak}/{MIN_HIGH_STREAK}) {'- Encore %d avant décompte!' % restants if restants > 0 else '- Séquence armée !'}")
            else:
                low_streak += 1
                high_streak = 0
                restants = MIN_LOW_STREAK - low_streak
                print(f"[{datetime.now().strftime('%H:%M:%S')}] PIR LOW ({low_streak}/{MIN_LOW_STREAK}) {'- Encore %d avant réarmement.' % restants if restants > 0 else '- Réarmement imminent.'}")

            # Validation de présence après X HIGH consécutifs
            if not intrusion_mode and high_streak == MIN_HIGH_STREAK:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] === {MIN_HIGH_STREAK} HIGH consécutifs détectés : DÉBUT DU DÉCOMPTE ALERTE INTRUS ({ALERT_TIMEOUT}s) ===")
                intrusion_mode = True
                detection_time = now
                intrus_sent = False

            # Détection de 4 LOW consécutifs → on réarme tout
            if intrusion_mode and low_streak == MIN_LOW_STREAK:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] === {MIN_LOW_STREAK} LOW consécutifs détectés : SYSTÈME RÉARMÉ ===")
                intrusion_mode = False
                high_streak = 0
                low_streak = 0
                detection_time = 0
                intrus_sent = False

            # --- Gestion bouton sonnette ---
            if bell_pressed and now - last_bell > COOLDOWN:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  Bouton pressé")
                play_bip()
                if intrusion_mode:
                    send_event("bell")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sonnerie pendant alerte : annulation du cycle alerte/intrus.")
                    intrusion_mode = False
                    high_streak = 0
                    low_streak = 0
                    detection_time = 0
                    intrus_sent = False
                else:
                    send_event("bell")
                last_bell = now
                while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                    time.sleep(0.1)

            # --- Déclenchement alerte intrus si temps écoulé ---
            if intrusion_mode and not intrus_sent and (now - detection_time > ALERT_TIMEOUT):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ INTRUS détecté (pas de sonnette après {ALERT_TIMEOUT}s)")
                send_event("intrus")
                intrus_sent = True  # Une seule alerte par présence

            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt demandé, nettoyage GPIO...")
        GPIO.cleanup()

if __name__ == '__main__':
    main_loop()
