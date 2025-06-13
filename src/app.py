from flask import Flask, render_template, redirect, url_for, jsonify
import threading
import time
import RPi.GPIO as GPIO
from datetime import datetime

# === CONFIGURATION ===
SPEAKER_PIN = 17
TOUCH_PIN = 22
PIR_PIN = 14

ALERT_TIMEOUT = 20  # délai max pour sonner après détection (en secondes)
INTRUS_ALERT_INTERVAL = 10  # intervalle pour renvoyer l'alerte intrus si présence continue (en secondes)

events = {
    "bell": [],
    "intrus": []
}

GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
GPIO.setup(TOUCH_PIN, GPIO.IN)
GPIO.setup(PIR_PIN, GPIO.IN)

pwm = GPIO.PWM(SPEAKER_PIN, 1000)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def play_bip(duration=0.3):
    pwm.start(50)
    time.sleep(duration)
    pwm.stop()

def hardware_listener():
    last_bell = 0
    intrusion_mode = False
    pir_detection_time = 0
    intrus_last_alert = 0
    while True:
        now = time.time()
        pir_detected = GPIO.input(PIR_PIN) == GPIO.HIGH
        sonnetted = GPIO.input(TOUCH_PIN) == GPIO.HIGH

        # Gestion sonnette : priorité absolue, annule alerte en cours
        if sonnetted:
            if now - last_bell > 2:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                events["bell"].insert(0, {"timestamp": ts})
                log(f"🔔 Sonnerie détectée à {ts} ! Réinitialisation de toute alerte.")
                play_bip()
                last_bell = now
                # Annule toute alerte/intrusion potentielle (reset cycle)
                if intrusion_mode:
                    log("La personne a sonné pendant la période de détection PIR, pas d'alerte intrus envoyée.")
                intrusion_mode = False
                pir_detection_time = 0
                intrus_last_alert = 0

        # Si détection PIR ET PAS en mode intrusion (nouvelle détection)
        if pir_detected and not intrusion_mode:
            intrusion_mode = True
            pir_detection_time = now
            intrus_last_alert = 0
            log("🕴️ Mouvement détecté ! Début du délai d'attente pour la sonnette...")

        # Si mode intrusion (donc détection PIR), pas de sonnette dans les 20s -> alerte
        if intrusion_mode:
            if not pir_detected:
                if pir_detection_time != 0:
                    log(f"Fin de la détection de mouvement. Durée présence : {int(now - pir_detection_time)}s.")
                intrusion_mode = False
                pir_detection_time = 0
                intrus_last_alert = 0
            else:
                time_since_pir = now - pir_detection_time
                if time_since_pir < ALERT_TIMEOUT:
                    log(f"Attente de sonnette ({int(time_since_pir)}/{ALERT_TIMEOUT}s)...")
                else:
                    # Envoie alerte toutes les INTRUS_ALERT_INTERVAL secondes tant que PIR est détecté
                    if (now - intrus_last_alert) > INTRUS_ALERT_INTERVAL:
                        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        events["intrus"].insert(0, {"timestamp": ts})
                        log(f"🚨 ALERTE INTRUS envoyée à {ts} ! (présence détectée depuis {int(time_since_pir)}s)")
                        intrus_last_alert = now

        time.sleep(0.5)  # 0.1s était peut-être trop rapide pour le spam log, tu peux baisser si besoin

listener_thread = threading.Thread(target=hardware_listener, daemon=True)
listener_thread.start()

app = Flask(__name__)

@app.route('/api/events')
def api_events():
    return jsonify({
        "bell_events": events["bell"][:10],
        "intrus_events": events["intrus"][:10]
    })

@app.route('/api/state')
def api_state():
    return jsonify({
        "bell": GPIO.input(TOUCH_PIN) == GPIO.HIGH,
        "intrus": len(events["intrus"]) > 0  # Affiche juste si une alerte récente existe
    })

@app.route('/')
def index():
    bell_events = events["bell"][:10]
    intrus_events = events["intrus"][:10]
    current_bell = GPIO.input(TOUCH_PIN) == GPIO.HIGH
    current_intrus = len(events["intrus"]) > 0
    return render_template('index.html', bell_events=bell_events, intrus_events=intrus_events,
                           current_bell=current_bell, current_intrus=current_intrus)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/reset', methods=['POST'])
def reset():
    events["bell"].clear()
    events["intrus"].clear()
    return redirect(url_for('admin'))

import atexit
@atexit.register
def cleanup():
    pwm.stop()
    GPIO.cleanup()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
