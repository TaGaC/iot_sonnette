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
MIN_PIR_HITS = 3   # nombre de détections PIR pour valider une présence

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
    pir_hits = 0
    pir_window_start = 0
    waiting_for_bell = False
    detection_time = 0
    intrus_sent = False

    print(" Système prêt. Attente capteur et/ou bouton...")

    try:
        while True:
            now = time.time()
            pir_detected = GPIO.input(PIR_PIN) == GPIO.HIGH
            bell_pressed = GPIO.input(TOUCH_PIN) == GPIO.HIGH

            # --- GESTION PIR ---
            if pir_detected:
                if pir_hits == 0:
                    pir_window_start = now
                pir_hits += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] PIR detecté ({pir_hits}/{MIN_PIR_HITS})")
                time.sleep(0.2)
            else:
                if pir_hits and now - pir_window_start > 2:
                    # Si ça fait plus de 2s sans détection, on reset les coups
                    pir_hits = 0
                    pir_window_start = 0

            # Si présence confirmée par PIR (3 détections)
            if pir_hits >= MIN_PIR_HITS and not waiting_for_bell:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Présence validée, attente éventuelle de sonnette {ALERT_TIMEOUT}s")
                detection_time = now
                waiting_for_bell = True
                intrus_sent = False  # reset flag pour cette séquence

            # --- GESTION SONNETTE ---
            if bell_pressed and now - last_bell > COOLDOWN:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  Bouton pressé")
                play_bip()
                if waiting_for_bell:
                    send_event("bell")
                    waiting_for_bell = False
                    pir_hits = 0
                else:
                    # S'il n'y a pas de séquence PIR en cours, c'est une sonnette normale
                    send_event("bell")
                last_bell = now
                # Attendre relâchement
                while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                    time.sleep(0.1)

            # --- GESTION ALERTE INTRUS ---
            if waiting_for_bell and not intrus_sent and (now - detection_time > ALERT_TIMEOUT):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ INTRUS détecté (pas de sonnette après {ALERT_TIMEOUT}s)")
                send_event("intrus")
                intrus_sent = True
                waiting_for_bell = False
                pir_hits = 0

            time.sleep(0.05)
    except KeyboardInterrupt:
        print(" Arrêt demandé, nettoyage GPIO...")
        GPIO.cleanup()

if __name__ == '__main__':
    main_loop()
