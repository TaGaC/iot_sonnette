from flask import Flask, render_template, redirect, url_for, jsonify
import threading
import time
import RPi.GPIO as GPIO
from datetime import datetime

# === CONFIGURATION ===
SPEAKER_PIN = 17
TOUCH_PIN = 22
PIR_PIN = 20

ALERT_TIMEOUT = 20  # délai en secondes après détection PIR
MOTION_LOG_COOLDOWN = 60  # on ne log qu'une détection par minute (en secondes)

events = {
    "bell": [],
    "intrus": []
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
    last_bell = 0
    last_motion_log = 0
    pending_alert = False
    detection_time = 0

    while True:
        now = time.time()

        # 1. Gestion bouton sonnette
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            if now - last_bell > 2:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                events["bell"].insert(0, {"timestamp": ts})
                print(f"? Sonnerie à {ts}")
                play_bip()
                last_bell = now
                # Si une alerte était en attente suite à détection PIR, on l'annule
                pending_alert = False
                detection_time = 0

        # 2. Gestion capteur IR (mouvement)
        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            # Log une seule fois par minute max
            if now - last_motion_log > MOTION_LOG_COOLDOWN:
                print(f"?? Présence détectée à {datetime.now().strftime('%H:%M:%S')}")
                last_motion_log = now
                # Début du timer pour une éventuelle alerte
                pending_alert = True
                detection_time = now

        # 3. Déclenchement alerte intrus
        if pending_alert and (now - detection_time > ALERT_TIMEOUT):
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            events["intrus"].insert(0, {"timestamp": ts})
            print(f"? INTRUS (pas de sonnette après détection IR) à {ts}")
            pending_alert = False  # Une seule alerte pour ce cas

        time.sleep(0.1)

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
        "intrus": len(events["intrus"]) > 0 and (time.time() - time.mktime(datetime.strptime(events["intrus"][0]['timestamp'], "%Y-%m-%d %H:%M:%S").timetuple()) < ALERT_TIMEOUT)
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
