import time
from collections import deque
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Initialisation I2C et ADC (A1)
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P1)

# Paramètres détection
window_size = 10     # Taille de la fenêtre glissante (ex: 10 mesures ~0.2 sec si refresh = 0.02)
refresh = 0.02       # Délai entre mesures (20ms = 50 mesures/seconde)
SEUIL = 0.02        # Seuil à ajuster selon tes tests ! (ex: 0.010 à 0.020 V)

window = deque([0]*window_size, maxlen=window_size)
last_detection = 0
min_interval = 1.0   # Minimum 1 seconde entre deux détections (pour éviter le spam)

print("Détection de bruit démarrée ! (seuil : {:.3f} V)".format(SEUIL))
print("Appuie sur Ctrl+C pour arrêter.")

try:
    while True:
        v = chan.voltage
        window.append(v)
        max_val = max(window)

        # Si bruit détecté ET assez de temps écoulé depuis la dernière détection
        if max_val > SEUIL and (time.time() - last_detection) > min_interval:
            print(f"Bruit détecté ! Max fenêtre : {max_val:.3f} V")
            last_detection = time.time()

        time.sleep(refresh)

except KeyboardInterrupt:
    print("\nArrêt du programme.")
