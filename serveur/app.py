from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import pytz
import os
import time
import json
from pywebpush import webpush, WebPushException
from sqlalchemy.dialects.sqlite import JSON


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sonnette.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SECRET_KEY = os.environ.get("SONNETTE_SECRET", "super_secret")

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
    
# Nouvelle table pour les abonnements Push
class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscription = db.Column(JSON, nullable=False)
    
    
    
VAPID_PUBLIC_KEY = os.environ.get("MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEK1C4gCx4QpJU2XDku1w+kFwDybyMfIH5VZM1kstuJpqi2wRtWt17BJbm2Tg7eh/lSAB3Uvq72sPdIxt6OoA+0w==")
VAPID_PRIVATE_KEY = os.environ.get("MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgmvn92xFm2TrD6pS714Uavv07LtY8Gp7Ib51clskV6JShRANCAAQrULiALHhCklTZcOS7XD6QXAPJvIx8gflVkzWSy24mmqLbBG1a3XsElubZODt6H+VIAHdS+rvaw90jG3o6gD7T")

def notify_all_intrus():
    subs = PushSubscription.query.all()
    payload = json.dumps({
        "title": "🚨 Intrus détecté",
        "body": "Un mouvement a été détecté près de la sonnette !",
        "icon": "/static/intrus.png"
    })
    for sub in subs:
        try:
            webpush(
                subscription_info=sub.subscription,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:admin@example.com"}
            )
        except WebPushException as ex:
            print(f"[!] Notification échouée : {ex}")


with app.app_context():
    db.create_all()

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
        return jsonify({"status": "bell event recorded"})
    elif evt_type == "intrus":
        db.session.add(IntrusEvent(timestamp=ts))
        db.session.commit()
        notify_all_intrus()
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

# Route pour s’abonner
@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    new_sub = PushSubscription(subscription=data)
    db.session.add(new_sub)
    db.session.commit()
    return jsonify({"status": "subscribed"})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
