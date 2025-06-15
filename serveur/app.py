from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime, timezone
import pytz
import os
import time
import json
from functools import wraps
from pywebpush import webpush, WebPushException

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sonnette.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("FLASK_SECRET", "changemeplz")
SECRET_KEY = os.environ.get("SONNETTE_SECRET", "super_secret")

VAPID_PRIVATE_KEY = "4QDH4NRlxvtLVaMcPQkChf80j1DP5TPqV9JUTgsLPFc"
VAPID_PUBLIC_KEY  = "BA89zCzXgx5Ulz-p4_IyEMsbzofxWv7d1px-5648i9UCXj57vGnv_DmLYKdQ1JmxG5eRYN5Pp1czQbjOA66Z6Hg"
VAPID_CLAIMS = {"sub": "mailto:thomas.jeanjacquot@telecomnancy.net"}

db = SQLAlchemy(app)
CANADA_TZ = pytz.timezone("America/Toronto")

@app.template_filter('to_local')
def to_local(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CANADA_TZ).strftime("%Y-%m-%d %H:%M:%S")

# ==== DB MODELS ====
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

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

with app.app_context():
    db.create_all()

# ==== AUTH ====
def is_logged_in():
    return session.get('logged_in', False)

def current_user():
    if not is_logged_in():
        return None
    return session.get('user')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("Connexion requise.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['logged_in'] = True
            session['user'] = username
            flash("Connexion réussie.", "success")
            return redirect(url_for('index'))
        else:
            error = "Identifiant ou mot de passe incorrect."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for('login'))

# ==== FONCTIONS PRINCIPALES ====
def send_notification_to_all(title, message):
    subs = PushSubscription.query.all()
    payload = json.dumps({
        "title": title,
        "body": message,
        "icon": "/static/icon.png"
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
@login_required
def index():
    bells = BellEvent.query.order_by(BellEvent.timestamp.desc()).limit(10).all()
    intrus = IntrusEvent.query.order_by(IntrusEvent.timestamp.desc()).limit(10).all()
    return render_template("index.html", bell_events=bells, intrus_events=intrus)

@app.route('/admin')
@login_required
def admin():
    return render_template("admin.html",
        bell_events=BellEvent.query.count(),
        intrus_events=IntrusEvent.query.count()
    )

@app.route('/reset', methods=['POST'])
@login_required
def reset():
    BellEvent.query.delete()
    IntrusEvent.query.delete()
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/stream')
@login_required
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
