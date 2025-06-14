from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask import Response, stream_with_context
import time
import json
import pytz
QC_TZ = pytz.timezone('America/Toronto') 

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sonnette.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SECRET_KEY = os.environ.get("SONNETTE_SECRET", "super_secret")

db = SQLAlchemy(app)

# === Modèles de base de données ===
class BellEvent(db.Model):
    __tablename__ = 'bell_events'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)

class IntrusEvent(db.Model):
    __tablename__ = 'intrus_events'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)

with app.app_context():
    db.create_all()

# === Route d'accueil ===
@app.route('/')
def index():
    bells = BellEvent.query.order_by(BellEvent.timestamp.desc()).limit(10).all()
    intrus = IntrusEvent.query.order_by(IntrusEvent.timestamp.desc()).limit(10).all()
    return render_template("index.html", 
        bell_events=[b.timestamp.astimezone(QC_TZ).strftime('%Y-%m-%d %H:%M:%S') for b in bells],
        intrus_events=[i.timestamp.astimezone(QC_TZ).strftime('%Y-%m-%d %H:%M:%S') for i in intrus]
    )


# === Route admin ===
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

# === API pour les requêtes du Raspberry ===
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
        return jsonify({"status": "intrus event recorded"})
    else:
        return jsonify({"error": "invalid type"}), 400
    
    
@app.route('/stream')
def stream():
    @stream_with_context
    def event_stream():
        while True:
            bells = [b.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                     for b in BellEvent.query.order_by(BellEvent.timestamp.desc()).limit(10).all()]
            intrus = [i.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                      for i in IntrusEvent.query.order_by(IntrusEvent.timestamp.desc()).limit(10).all()]
            state = {
                'bell': bool(bells),
                'intrus': bool(intrus),
                'bell_events': bells,
                'intrus_events': intrus
            }
            yield f"data: {json.dumps(state)}\n\n"
            time.sleep(2)
    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
