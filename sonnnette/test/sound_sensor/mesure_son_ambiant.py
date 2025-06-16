# Permet de mesurer le niveau sonore ambiant à l'aide d'un capteur analogique et ainsi fixer les différents seuils de détection

import time
from collections import deque
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P1)

refresh = 0.02
periode_moyenne = 5.0
buffer_size = int(periode_moyenne / refresh)
valeurs = deque(maxlen=buffer_size)

print("Mesure du niveau sonore (précision 0,0001V) sur A1 (valeur absolue).")
print(f"Affichage instantané, moyenne sur {periode_moyenne} secondes.")
print("Appuie sur Ctrl+C pour arrêter.\n")

dernier_affichage = time.time()

try:
    while True:
        v = abs(chan.voltage)   # <-- Valeur absolue !
        valeurs.append(v)
        print(f"Valeur instantanée : {v:.4f} V")

        now = time.time()
        if now - dernier_affichage >= periode_moyenne:
            moyenne = sum(valeurs) / len(valeurs)
            print(f"\n--> Moyenne sur {periode_moyenne:.1f} sec : {moyenne:.4f} V\n")
            dernier_affichage = now

        time.sleep(refresh)

except KeyboardInterrupt:
    print("\nArrêt du programme.")
