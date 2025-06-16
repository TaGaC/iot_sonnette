import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import matplotlib.pyplot as plt
from collections import deque
import numpy as np

# Initialisation I2C et ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P1)   # <--- A1 utilisé ici

# Paramètres graphe
window_size = 200
refresh = 0.02
y_lim_v = (0, 5.0)   # 5V car alim en 5V
y_lim_db = (0, 80)   # 0 à 80 dB arbitraires (à ajuster)

data_v = deque([0]*window_size, maxlen=window_size)
data_db = deque([0]*window_size, maxlen=window_size)

# Pour éviter log(0), on définit un bruit de fond minimal (valeur au repos)
V_REF = 0.01  # Tension de référence de base (en V, ajuster selon ton bruit de fond réel)

plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
line_v, = ax1.plot(data_v, label="Tension (V)")
ax1.set_ylim(y_lim_v)
ax1.set_ylabel("Tension (V)")
ax1.set_title("Microphone analogique (DFR0034) sur A1")

line_db, = ax2.plot(data_db, label="Niveau sonore (dB, relatif)")
ax2.set_ylim(y_lim_db)
ax2.set_xlabel("Échantillons (temps)")
ax2.set_ylabel("dB (relatif)")
ax2.set_title("Valeur relative en décibels (log10)")

plt.tight_layout()

try:
    while True:
        v = chan.voltage
        data_v.append(v)
        # Conversion logarithmique (dB relatif)
        db = 20 * np.log10(max(v, V_REF)/V_REF)
        data_db.append(db)

        line_v.set_ydata(data_v)
        line_db.set_ydata(data_db)
        ax1.relim()
        ax1.autoscale_view(True, True, False)
        ax2.relim()
        ax2.autoscale_view(True, True, False)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(refresh)
except KeyboardInterrupt:
    pass
finally:
    plt.ioff()
    plt.show()
