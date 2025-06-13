from flask import Flask, render_template, redirect, url_for, jsonify
import threading
import time
import RPi.GPIO as GPIO
from datetime import datetime

# === CONFIGURATION ===
SPEAKER_PIN = 17      # GPIO pour le haut-parleur
TOUCH_PIN = 22        # GPIO pour le bouton tactile
PIR_PIN = 14          # GPIO pour le capteur IR

# === STOCKAGE DES ÉVÉNEMENTS ===
events = {
    "bell": [],
    "motion": []
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
    pir_streak = 0
    pir_triggered = False
    cooldown = 2
    PIR_THRESHOLD = 10      # nombre de détections pour sonner
    PIR_MAX_IDLE = 1.0      # durée max (en s) entre deux détections pour compter la série

    while True:
        now = time.time()

        # Bouton tactile
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            if now - last_touch > cooldown:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                events["bell"].insert(0, {"timestamp": ts})
                print(f"🔔 Sonnerie à {ts} (bouton)")
                play_bip()
                last_touch = now

        # PIR
        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            # Détection continue
            if now - last_pir < PIR_MAX_IDLE:
                pir_streak += 1
            else:
                pir_streak = 1  # Nouvelle série

            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            events["motion"].insert(0, {"timestamp": ts})
            print(f"🕴️ Mouvement détecté à {ts} (streak: {pir_streak})")
            last_pir = now

            if pir_streak >= PIR_THRESHOLD and not pir_triggered:
                print("🚨 PIR a détecté 10 fois d'affilé : ALARME SONORE !")
                play_bip(0.6)
                pir_triggered = True
        else:
            # Reset si PIR n'a rien détecté pendant plus de PIR_MAX_IDLE secondes
            if now - last_pir > PIR_MAX_IDLE:
                pir_streak = 0
                pir_triggered = False

        time.sleep(0.05)

listener_thread = threading.Thread(target=hardware_listener, daemon=True)
listener_thread.start()

app = Flask(__name__)

@app.route('/')
def index():
    bell_events = events["bell"][:10]
    motion_events = events["motion"][:10]
    current_bell = GPIO.input(TOUCH_PIN) == GPIO.HIGH
    current_motion = GPIO.input(PIR_PIN) == GPIO.HIGH
    return render_template('index.html', bell_events=bell_events, motion_events=motion_events,
                           current_bell=current_bell, current_motion=current_motion)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/reset', methods=['POST'])
def reset():
    events["bell"].clear()
    events["motion"].clear()
    return redirect(url_for('admin'))

@app.route('/api/state')
def api_state():
    return jsonify({
        "bell": GPIO.input(TOUCH_PIN) == GPIO.HIGH,
        "motion": GPIO.input(PIR_PIN) == GPIO.HIGH
    })

import atexit
@atexit.register
def cleanup():
    pwm.stop()
    GPIO.cleanup()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
