from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import pytz
import os
import time
import json
from pywebpush import webpush, WebPushException

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sonnette.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SECRET_KEY = os.environ.get("SONNETTE_SECRET", "super_secret")

VAPID_PRIVATE_KEY = "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgGDn1mJ4wYLjsyVR4wSblA8svjmBuqlNj2FtoEPOccZKhRANCAATsQaveWT254M7jKIJp2q0iX8FiusKsyOTN3lGhGUA9nLg7yc/ERtGKnN1dkl8dVuHVph9k6kSbh2iTwc5VE4F8"  # ta clé privée
VAPID_PUBLIC_KEY  = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE7EGr3lk9ueDO4yiCadqtIl_BYrrCrMjkzd5RoRlAPZy4O8nPxEbRipzdXZJfHVbh1aYfZOpEm4dok8HOVROBfA"
VAPID_CLAIMS = {"sub": "mailto:thomas.jeanjacquot@telecomnancy.net"}

db = SQLAlchemy(app)

# Utilise le fuseau Canada/Est (GMT-4 l’été, GMT-5 l’hiver)
CANADA_TZ = pytz.timezone("America/Toronto")  # change en "America/Montreal" si tu veux

# === Ajoute ce filtre Jinja2 ===
@app.template_filter('to_local')
def to_local(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CANADA_TZ).strftime("%Y-%m-%d %H:%M:%S")

# === Modèles de base de données ===
class BellEvent(db.Model):
    __tablename__ = 'bell_events'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)

class IntrusEvent(db.Model):
    __tablename__ = 'intrus_events'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    
    
class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)


with app.app_context():
    db.create_all()
    
    
def send_notification_to_all(title, message):
    subs = PushSubscription.query.all()
    payload = json.dumps({
        "title": title,
        "body": message,
        "icon": "/static/bell.png"  # optionnel
    })
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            print("Erreur push:", e)

@app.route('/')
def index():
    bells = BellEvent.query.order_by(BellEvent.timestamp.desc()).limit(10).all()
    intrus = IntrusEvent.query.order_by(IntrusEvent.timestamp.desc()).limit(10).all()
    return render_template("index.html", bell_events=bells, intrus_events=intrus)

@app.route('/admin')
def admin():
    return render_template("admin.html",
        bell_events=BellEvent.query.count(),
        intrus_events=IntrusEvent.query.count()
    )

@app.route('/reset', methods=['POST'])
def reset():
    BellEvent.query.delete()
    IntrusEvent.query.delete()
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/api/sonnette', methods=['POST'])
def receive_sonnette():
    data = request.get_json()
    if not data or data.get("secret") != SECRET_KEY:
        return jsonify({"error": "unauthorized"}), 401

    evt_type = data.get("type")
    ts_raw = data.get("timestamp")
    try:
        ts = datetime.fromisoformat(ts_raw)
    except:
        return jsonify({"error": "invalid timestamp"}), 400

    if evt_type == "bell":
        db.session.add(BellEvent(timestamp=ts))
        db.session.commit()
        send_notification_to_all("🔔 Nouvelle alerte", "Quelqu’un a sonné à la porte.")
        return jsonify({"status": "bell event recorded"})
    elif evt_type == "intrus":
        db.session.add(IntrusEvent(timestamp=ts))
        db.session.commit()
        send_notification_to_all("🚨 Détection d’intrus", "Un mouvement a été détecté.")
        return jsonify({"status": "intrus event recorded"})
    else:
        return jsonify({"error": "invalid type"}), 400

@app.route('/stream')
def stream():
    @stream_with_context
    def event_stream():
        while True:
            bells = [
                to_local(b.timestamp)
                for b in BellEvent.query.order_by(BellEvent.timestamp.desc()).limit(10).all()
            ]
            intrus = [
                to_local(i.timestamp)
                for i in IntrusEvent.query.order_by(IntrusEvent.timestamp.desc()).limit(10).all()
            ]
            state = {
                'bell': bool(bells),
                'intrus': bool(intrus),
                'bell_events': bells,
                'intrus_events': intrus
            }
            yield f"data: {json.dumps(state)}\n\n"
            time.sleep(2)
    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    if not data or 'endpoint' not in data:
        return jsonify({'error': 'Invalid subscription'}), 400

    sub = PushSubscription(
        endpoint=data['endpoint'],
        p256dh=data['keys']['p256dh'],
        auth=data['keys']['auth']
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({'status': 'subscribed'})



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)

