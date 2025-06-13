from flask import Flask, render_template, redirect, url_for, jsonify, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
import threading
import time
import RPi.GPIO as GPIO
from datetime import datetime
import atexit
import json


# === Initialisation de l'application Flask et de la DB ===
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sonnette.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# === Définition des modèles ===
class BellEvent(db.Model):
    __tablename__ = 'bell_events'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)

class IntrusEvent(db.Model):
    __tablename__ = 'intrus_events'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)

# === Création des tables si nécessaire ===
with app.app_context():
    db.create_all()

# === Configuration GPIO ===
SPEAKER_PIN = 17  # GPIO pour le haut-parleur
TOUCH_PIN   = 22  # GPIO pour le bouton tactile
PIR_PIN     = 14  # GPIO pour le capteur PIR (désactivé)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
gpio_pull = GPIO.PUD_DOWN
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=gpio_pull)
GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=gpio_pull)

pwm = GPIO.PWM(SPEAKER_PIN, 1000)

def play_bip(duration=0.3):
    pwm.start(50)
    time.sleep(duration)
    pwm.stop()

# === Thread d'écoute hardware ===
def hardware_listener():
    last_touch = 0
    cooldown = 5  # secondes
    while True:
        now = time.time()
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH and (now - last_touch) > cooldown:
            ts = datetime.now()
            with app.app_context():  # ensure context for DB
                evt = BellEvent(timestamp=ts)
                db.session.add(evt)
                db.session.commit()
            print(f"🔔 Sonnerie détectée à {ts}")
            play_bip()
            last_touch = now
            # anti-rebond: attendre relâchement
            while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                time.sleep(0.1)
        time.sleep(0.05)

listener_thread = threading.Thread(target=hardware_listener, daemon=True)
listener_thread.start()

# === Server-Sent Events (push) ===
@app.route('/stream')
def stream():
    @stream_with_context
    def event_stream():
        while True:
            # Requête en base (dans request context)
            bells = [b.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                     for b in BellEvent.query.order_by(BellEvent.timestamp.desc()).limit(10).all()]
            intrus = [i.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                      for i in IntrusEvent.query.order_by(IntrusEvent.timestamp.desc()).limit(10).all()]
            state = {
                'bell': GPIO.input(TOUCH_PIN) == GPIO.HIGH,
                'intrus': False,
                'bell_events': bells,
                'intrus_events': intrus
            }
            yield f"data: {json.dumps(state)}\n\n"
            time.sleep(2)
    return Response(event_stream(), mimetype='text/event-stream')

# === Routes classiques ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    bell_count = BellEvent.query.count()
    intrus_count = IntrusEvent.query.count()
    return render_template('admin.html', bell_count=bell_count, intrus_count=intrus_count)

@app.route('/reset', methods=['POST'])
def reset():
    with app.app_context():
        BellEvent.query.delete()
        IntrusEvent.query.delete()
        db.session.commit()
    return redirect(url_for('admin'))

# === Nettoyage GPIO ===
@atexit.register
def cleanup():
    pwm.stop()
    GPIO.cleanup()

if __name__ == '__main__':
    # Désactive le reloader pour éviter double démarrage
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
