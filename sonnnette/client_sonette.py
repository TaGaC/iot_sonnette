import RPi.GPIO as GPIO
import time
import requests
from datetime import datetime

# === CONFIGURATION ===
SPEAKER_PIN = 17
TOUCH_PIN = 22
COOLDOWN = 4  # secondes
SERVER_URL = "http://145.79.6.244:5000/api/sonnette"  # à modifier
SECRET_KEY = "super_secret"  # clé partagée avec le serveur

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
pwm = GPIO.PWM(SPEAKER_PIN, 1000)

def play_bip():
    melody = [(523, 0.2), (659, 0.2), (784, 0.2), (1046, 0.3)]
    for freq, dur in melody:
        pwm.ChangeFrequency(freq)
        pwm.start(50)
        time.sleep(dur)
        pwm.stop()
        time.sleep(0.05)

def send_bell_event():
    payload = {
        "type": "bell",
        "timestamp": datetime.utcnow().isoformat(),
        "secret": SECRET_KEY
    }
    try:
        r = requests.post(SERVER_URL, json=payload, timeout=3)
        if r.ok:
            print(f"[{datetime.now().strftime('%H:%M:%S')}]  Événement envoyé.")
        else:
            print(f"[!]  Erreur serveur : {r.status_code}")
    except Exception as e:
        print(f"[!]  Erreur réseau : {e}")

def main_loop():
    last_trigger = 0
    print(" Système prêt. Appuyez sur le bouton...")
    try:
        while True:
            if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                now = time.time()
                if now - last_trigger > COOLDOWN:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}]  Bouton pressé")
                    play_bip()
                    send_bell_event()
                    last_trigger = now
                while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                    time.sleep(0.1)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print(" Arrêt demandé, nettoyage GPIO...")
        GPIO.cleanup()

if __name__ == '__main__':
    main_loop()
