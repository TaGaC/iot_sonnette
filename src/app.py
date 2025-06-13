from flask import Flask, render_template, redirect, url_for, jsonify
import threading
import time
import RPi.GPIO as GPIO
from datetime import datetime

# === CONFIGURATION ===
SPEAKER_PIN = 17      # GPIO pour le haut-parleur
TOUCH_PIN = 22        # GPIO pour le bouton tactile
PIR_PIN = 14          # GPIO pour le capteur IR

DETECTION_TIMEOUT = 20  # secondes sans sonnerie après détection PIR = alerte (modifie ici)
INTRUS_ALERT_COOLDOWN = 10  # envoie une alerte toutes les X secondes en cas de présence persistante

events = {
    "bell": [],     # historique des sonneries
    "motion": [],   # historique des détections IR (mouvement simple)
    "intrus": []    # historique des alertes "intrus"
}

GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
GPIO.setup(TOUCH_PIN, GPIO.IN)
GPIO.setup(PIR_PIN, GPIO.IN)

pwm = GPIO.PWM(SPEAKER_PIN, 1000)

def play_bip(duration=0.3):
    pwm.start(50)
    time.sleep(duration)
    pwm.stop()

def hardware_listener():
    last_touch = 0
    last_pir = 0
    last_intrus_alert = 0
    possible_intrus = False
    detection_start_time = 0
    cooldown = 2  # entre deux sonnettes

    while True:
        now = time.time()

        # === Gestion BOUTON (sonnette) ===
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            if now - last_touch > cooldown:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                events["bell"].insert(0, {"timestamp": ts})
                print(f"🔔 Sonnerie à {ts} (bouton)")
                play_bip()
                last_touch = now
                # Si quelqu'un sonne, on annule toute alerte "intrus" potentielle
                possible_intrus = False
                detection_start_time = 0

        # === Gestion MOUVEMENT IR ===
        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            if now - last_pir > 1.5:  # anti-spam pour l'historique
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                events["motion"].insert(0, {"timestamp": ts})
                print(f"🕴️ Mouvement détecté à {ts}")
                last_pir = now
            # Début d'une nouvelle présence
            if not possible_intrus:
                possible_intrus = True
                detection_start_time = now

            # Si la présence PIR continue ET PAS de sonnette, alerte "intrus"
            if possible_intrus and (now - detection_start_time) > DETECTION_TIMEOUT:
                # Évite le spam d'alerte (n'envoie qu'une fois toutes les X secondes)
                if now - last_intrus_alert > INTRUS_ALERT_COOLDOWN:
                    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    events["intrus"].insert(0, {"timestamp": ts})
                    print(f"🚨 INTRUS détecté à {ts} !")
                    last_intrus_alert = now
        else:
            # Dès qu'il n'y a plus de présence, on réinitialise le timer de surveillance
            possible_intrus = False
            detection_start_time = 0

        time.sleep(0.1)

listener_thread = threading.Thread(target=hardware_listener, daemon=True)
listener_thread.start()

app = Flask(__name__)

@app.route('/api/events')
def api_events():
    return jsonify({
        "bell_events": events["bell"][:10],
        "motion_events": events["motion"][:10],
        "intrus_events": events["intrus"][:10]
    })

@app.route('/api/state')
def api_state():
    return jsonify({
        "bell": GPIO.input(TOUCH_PIN) == GPIO.HIGH,
        "motion": GPIO.input(PIR_PIN) == GPIO.HIGH,
        "intrus": len(events["intrus"]) > 0 and (time.time() - time.mktime(datetime.strptime(events["intrus"][0]['timestamp'], "%Y-%m-%d %H:%M:%S").timetuple()) < INTRUS_ALERT_COOLDOWN)
    })

@app.route('/')
def index():
    bell_events = events["bell"][:10]
    motion_events = events["motion"][:10]
    intrus_events = events["intrus"][:10]
    current_bell = GPIO.input(TOUCH_PIN) == GPIO.HIGH
    current_motion = GPIO.input(PIR_PIN) == GPIO.HIGH
    current_intrus = len(events["intrus"]) > 0
    return render_template('index.html', bell_events=bell_events, motion_events=motion_events,
                           intrus_events=intrus_events, current_bell=current_bell,
                           current_motion=current_motion, current_intrus=current_intrus)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/reset', methods=['POST'])
def reset():
    events["bell"].clear()
    events["motion"].clear()
    events["intrus"].clear()
    return redirect(url_for('admin'))

import atexit
@atexit.register
def cleanup():
    pwm.stop()
    GPIO.cleanup()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
