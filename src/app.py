from flask import Flask, render_template, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
import time
import RPi.GPIO as GPIO
from datetime import datetime
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

# === Création des tables ===
with app.app_context():
    db.create_all()

# === CONFIGURATION GPIO ===
SPEAKER_PIN = 17
TOUCH_PIN   = 22
PIR_PIN     = 20  # non utilisé pour l'instant

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
pwm = GPIO.PWM(SPEAKER_PIN, 1000)

# === Fonction de sonnerie ===
def play_bip(duration=0.3):
    pwm.start(50)
    time.sleep(duration)
    pwm.stop()

# === Détection par callback avec debounce logiciel ===
last_touch = 0
COOLDOWN_MS = 5000  # intervalle minimal entre deux déclenchements (ms)

def my_callback(channel):
    global last_touch
    now_ms = int(time.time() * 1000)
    # Vérifier le cooldown pour éviter les doubles déclenchements
    if now_ms - last_touch < COOLDOWN_MS:
        return
    last_touch = now_ms
    ts = datetime.now()
    # Enregistrer en base de données dans le contexte Flask
    with app.app_context():
        evt = BellEvent(timestamp=ts)
        db.session.add(evt)
        db.session.commit()
    print(f"🔔 Sonnerie détectée à {ts.strftime('%Y-%m-%d %H:%M:%S')}")
    play_bip()

# Activer l'interruption sur front montant, avec bouncetime logiciel
GPIO.add_event_detect(TOUCH_PIN, GPIO.RISING, callback=my_callback, bouncetime=200)

# === Server-Sent Events (push updates) ===
@app.route('/stream')
def stream():
    # Pousser le contexte d'application pour les requêtes SQL dans le générateur
    ctx = app.app_context()
    ctx.push()

    def event_stream():
        while True:
            # Requête en base pour les 10 derniers événements sonnette
            bells = [b.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                     for b in BellEvent.query.order_by(BellEvent.timestamp.desc()).limit(10).all()]
            # Pas d'intrusion pour l'instant
            intrus = []
            state = {
                'bell': GPIO.input(TOUCH_PIN) == GPIO.HIGH,
                'intrus': False,
                'bell_events': bells,
                'intrus_events': intrus
            }
            yield f"data: {json.dumps(state)}\n\n"
            time.sleep(2)
    return Response(event_stream(), mimetype='text/event-stream')

# === Pages Web ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    with app.app_context():
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
import atexit
@atexit.register
def cleanup():
    pwm.stop()
    GPIO.cleanup()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
