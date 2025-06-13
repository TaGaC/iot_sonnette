from flask import Flask, render_template, redirect, url_for, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
import threading
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

# === Création des tables (si elles n'existent pas) ===
with app.app_context():
    db.create_all()

# === CONFIGURATION GPIO ===
SPEAKER_PIN = 17  # GPIO pour le haut-parleur
TOUCH_PIN   = 22  # GPIO pour le bouton tactile
PIR_PIN     = 20  # GPIO pour le capteur PIR (désactivé pour l'instant)

GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEAKER_PIN, GPIO.OUT)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

pwm = GPIO.PWM(SPEAKER_PIN, 1000)

def play_bip(duration=0.3):
    pwm.start(50)
    time.sleep(duration)
    pwm.stop()

# === Fonction d'écoute hardware ===
def hardware_listener():
    # Pousse le contexte d'application pour permettre db.session dans le thread
    ctx = app.app_context()
    ctx.push()

    last_touch = 0
    cooldown = 5  # secondes : délai minimum entre deux appuis

    while True:
        now = time.time()
        # Gestion bouton tactile (sonnette)
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            if now - last_touch > cooldown:
                ts = datetime.now()
                evt = BellEvent(timestamp=ts)
                db.session.add(evt)
                db.session.commit()
                print(f" Sonnerie détectée à {ts.strftime('%Y-%m-%d %H:%M:%S')}")
                play_bip()
                last_touch = now
                while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                    time.sleep(0.1)
        time.sleep(0.05)

# Démarrage du thread hardware
listener_thread = threading.Thread(target=hardware_listener, daemon=True)
listener_thread.start()

# === Server-Sent Events (push updates) ===
@app.route('/stream')
def stream():
    def event_stream():
        while True:
            # Construire l'état complet
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

# === Pages Web ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html',
                           bell_count=BellEvent.query.count(),
                           intrus_count=IntrusEvent.query.count())

@app.route('/reset', methods=['POST'])
def reset():
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
