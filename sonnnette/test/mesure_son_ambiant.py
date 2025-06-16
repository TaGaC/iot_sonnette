# PRogramme qui permet de mesurer le son ambiant capté par le microphone, afn d'établir une référence pour le seuil de détection de bruit.
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

# Paramètres
refresh = 0.02             # Mesure toutes les 20ms
periode_moyenne = 5.0      # Période de la moyenne (en secondes)
buffer_size = int(periode_moyenne / refresh)
valeurs = deque(maxlen=buffer_size)

print(f"Mesure du niveau sonore (précision 0,0001V) sur A1.")
print(f"Affichage instantané, moyenne sur {periode_moyenne} secondes.")
print("Appuie sur Ctrl+C pour arrêter.\n")

dernier_affichage = time.time()

try:
    while True:
        v = chan.voltage
        valeurs.append(v)
        print(f"Valeur instantanée : {v:.4f} V")
        
        # Affiche la moyenne toutes les X secondes
        now = time.time()
        if now - dernier_affichage >= periode_moyenne:
            moyenne = sum(valeurs) / len(valeurs)
            print(f"\n--> Moyenne sur {periode_moyenne:.1f} sec : {moyenne:.4f} V\n")
            dernier_affichage = now

        time.sleep(refresh)

except KeyboardInterrupt:
    print("\nArrêt du programme.")
