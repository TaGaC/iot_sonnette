import RPi.GPIO as GPIO
import time
import requests
from datetime import datetime
import threading
from collections import deque
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# === CONFIGURATION PRINCIPALE ===

SPEAKER_PIN = 17          # [GPIO] Broche GPIO du haut-parleur
TOUCH_PIN = 22            # [GPIO] Broche GPIO du capteur tactile (bouton)
PIR_PIN = 20              # [GPIO] Broche GPIO du capteur de mouvement PIR

COOLDOWN_BELL = 2         # [secondes] Temps anti-spam entre deux sonnettes (appuis bouton)
SERVER_URL = "https://smartsonnette.duckdns.org//api/sonnette"  # [URL] Adresse de l'API serveur
SECRET_KEY = "super_secret"         # [str] Clé secrète pour authentification API

ALERT_TIMEOUT = 20        # [secondes] Délai avant confirmation "intrus" si pas de sonnette
MIN_HIGH_STREAK = 8       # [nombre] Nombre de détections HIGH (mouvement) PIR nécessaires pour armer l’alerte
MIN_LOW_STREAK = 4        # [nombre] Nombre de détections LOW PIR consécutives pour réarmer le système

# === CONFIGURATION DÉTECTION BRUIT ===

SEUIL_BRUIT = 0.0040          # [volts] Seuil de tension pour considérer qu’un bruit est détecté (ADC)
DUREE_DETECTION_BRUIT = 2.0   # [secondes] Durée pendant laquelle le bruit doit être détecté en continu
FENETRE_BRUIT = 0.2           # [secondes] Fenêtre de temps utilisée pour la moyenne glissante sur la détection de bruit
REFRESH_BRUIT = 0.02          # [secondes] Intervalle de lecture du capteur de bruit (fréquence d'échantillonnage ADC)

# === ANTI-SPAM NOTIFICATIONS ===

NOTIF_COOLDOWN = 30.0         # [secondes] Temps minimum entre deux notifications envoyées du même type (anti-spam général)

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
            #print(f"[DEBUG] Envoi event : {evt_type}")
            print(f"[!]  Erreur serveur : {r.status_code}")
    except Exception as e:
        print(f"[!]  Erreur réseau : {e}")

# --- Thread pour la détection de bruit ---
class BruitDetector(threading.Thread):
    def __init__(self, seuil, duree_detection, fenetre, refresh):
        super().__init__()
        self.seuil = seuil
        self.duree_detection = duree_detection
        self.fenetre = fenetre
        self.refresh = refresh
        self.buffer_size = int(fenetre / refresh)
        self.nb_moyennes = int(duree_detection / fenetre)
        self.moyennes = deque([0]*self.nb_moyennes, maxlen=self.nb_moyennes)
        self.buffer = deque([0]*self.buffer_size, maxlen=self.buffer_size)
        self.bruit = False
        self._stop_flag = threading.Event()
        # Init ADC
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        self.chan = AnalogIn(ads, ADS.P1)

    def run(self):
        while not self._stop_flag.is_set():
            v = abs(self.chan.voltage)
            self.buffer.append(v)
            if len(self.buffer) == self.buffer_size:
                moyenne_fenetre = sum(self.buffer) / self.buffer_size
                self.moyennes.append(moyenne_fenetre)
                if all(m > self.seuil for m in self.moyennes):
                    self.bruit = True
                else:
                    self.bruit = False
            time.sleep(self.refresh)

    def stop(self):
        self._stop_flag.set()

def main_loop():
    print("Calibration du capteur PIR... Merci de ne pas bouger devant le capteur.")
    time.sleep(20)
    print("Calibration terminée. Système prêt. Attente capteur et/ou bouton...")

    last_bell = 0
    high_streak = 0
    low_streak = 0
    surveillance = False
    detection_time = 0
    cycle_completed = False
    last_pir_state = None  # Mémorise l’état PIR précédent

    # --- Initialisation du détecteur de bruit ---
    bruit_detector = BruitDetector(SEUIL_BRUIT, DUREE_DETECTION_BRUIT, FENETRE_BRUIT, REFRESH_BRUIT)
    bruit_detector.daemon = True
    bruit_detector.start()

    # --- Système de verrou pour notifications (1 verrou pour chaque combinaison possible) ---
    notif_locks = {
        "intrus_bruit": 0,
        "intrus_presence": 0,
        "intrus_presence_et_bruit": 0
    }

    try:
        while True:
            now = time.time()
            pir_state = GPIO.input(PIR_PIN) == GPIO.HIGH
            bell_pressed = GPIO.input(TOUCH_PIN) == GPIO.HIGH
            bruit = bruit_detector.bruit

            # === DEBUG : Affiche uniquement lors d'un changement d'état PIR ===
            #if pir_state != last_pir_state:
                #print(f"[{datetime.now().strftime('%H:%M:%S')}] [DEBUG] PIR passe {'HIGH (mouvement)' if pir_state else 'LOW (pas de mouvement)'}")
                #last_pir_state = pir_state

            # --- PHASE 1 : Attente de détection de présence (pas encore en surveillance) ---
            if not surveillance and not cycle_completed:
                if pir_state:
                    high_streak += 1
                    if high_streak <= MIN_HIGH_STREAK:
                        restants = MIN_HIGH_STREAK - high_streak
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] PIR HIGH ({high_streak}/{MIN_HIGH_STREAK}) {'- Encore %d avant décompte!' % restants if restants > 0 else '- Séquence armée !'}")
                    if high_streak == MIN_HIGH_STREAK:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] === {MIN_HIGH_STREAK} HIGH consécutifs détectés : DÉBUT DU DÉCOMPTE ALERTE INTRUS ({ALERT_TIMEOUT}s) ===")
                        surveillance = True
                        detection_time = now
                        low_streak = 0
                else:
                    if high_streak > 0:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] PIR repasse LOW, reset du compteur HIGH.")
                    high_streak = 0

            # --- PHASE 2 : Surveillance (présence validée) ---
            elif surveillance:
                if now - detection_time > ALERT_TIMEOUT:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ INTRUS détecté (pas de sonnette après {ALERT_TIMEOUT}s)")
                    send_event("intrus")
                    surveillance = False
                    cycle_completed = True
                    low_streak = 0
                elif not pir_state:
                    low_streak += 1
                    if low_streak <= MIN_LOW_STREAK:
                        restants = MIN_LOW_STREAK - low_streak
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] PIR LOW en surveillance ({low_streak}/{MIN_LOW_STREAK}) {'- Encore %d avant réarmement.' % restants if restants > 0 else '- Réarmement possible après événement.'}")
                else:
                    low_streak = 0

            # --- PHASE 3 : Cycle complété, attente du réarmement (4 LOW) ---
            elif cycle_completed:
                if not pir_state:
                    low_streak += 1
                    if low_streak <= MIN_LOW_STREAK:
                        restants = MIN_LOW_STREAK - low_streak
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] PIR LOW (réarmement) ({low_streak}/{MIN_LOW_STREAK}) {'- Encore %d avant système réarmé.' % restants if restants > 0 else '- SYSTÈME RÉARMÉ.'}")
                    if low_streak == MIN_LOW_STREAK:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] === {MIN_LOW_STREAK} LOW consécutifs détectés : SYSTÈME RÉARMÉ ===")
                        cycle_completed = False
                        high_streak = 0
                        low_streak = 0
                else:
                    low_streak = 0

            # --- GESTION SONNETTE ---
            if bell_pressed and now - last_bell > COOLDOWN_BELL:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  Bouton pressé")
                play_bip()
                if surveillance:
                    send_event("bell")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sonnerie pendant alerte : annulation du cycle alerte/intrus.")
                    surveillance = False
                    cycle_completed = True
                    low_streak = 0
                else:
                    send_event("bell")
                last_bell = now
                while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                    time.sleep(0.1)

            # --- GESTION NOTIFICATION INTRUS (BRUIT &/OU MOUVEMENT) ---
            notif_type = None
            if bruit and pir_state:
                notif_type = "intrus_presence_et_bruit"
            elif bruit and not pir_state:
                notif_type = "intrus_bruit"
            elif pir_state and not bruit:
                notif_type = "intrus_presence"

            if notif_type:
                last_sent = notif_locks[notif_type]
                if now - last_sent > NOTIF_COOLDOWN:
                    send_event(notif_type)
                    notif_locks[notif_type] = now
        


            time.sleep(1)

    except KeyboardInterrupt:
        print("Arrêt demandé, nettoyage GPIO...")
        bruit_detector.stop()
        bruit_detector.join()
        GPIO.cleanup()

if __name__ == '__main__':
    main_loop()
