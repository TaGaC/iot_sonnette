import time
from collections import deque
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- Paramètres modifiables ---
SEUIL = 0.0040           # Seuil de tension en volt
DUREE_DETECTION = 2.0    # Durée (secondes) de bruit à dépasser pour valider la présence
REFRESH = 0.02           # Temps entre mesures (20 ms = 50 mesures/seconde)
FENETRE = 0.2            # Durée de la fenêtre glissante pour la moyenne (en secondes)

# Calcul de la taille du buffer pour la fenêtre glissante
buffer_size = int(FENETRE / REFRESH)
moyennes = deque([0]*int(DUREE_DETECTION / FENETRE), maxlen=int(DUREE_DETECTION / FENETRE))

# --- Initialisation ADC ---
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P1)

print(f"Détection de présence sonore démarrée (seuil : {SEUIL:.4f} V, durée : {DUREE_DETECTION:.1f} s)")
print("Appuie sur Ctrl+C pour arrêter.\n")

try:
    buffer = deque([0]*buffer_size, maxlen=buffer_size)
    presence_detectee = False

    while True:
        v = abs(chan.voltage)
        buffer.append(v)

        # Toutes les FENETRE secondes, calcule la moyenne de la fenêtre et stocke-la
        if len(buffer) == buffer_size:
            moyenne_fenetre = sum(buffer) / buffer_size
            moyennes.append(moyenne_fenetre)

            # Vérifie si le son a dépassé le seuil pendant toute la durée voulue
            if all(m > SEUIL for m in moyennes):
                if not presence_detectee:
                    print(f"\n>> Présence détectée ! Son moyen > {SEUIL:.4f} V pendant {DUREE_DETECTION:.1f} s <<\n")
                    presence_detectee = True
            else:
                if presence_detectee:
                    print("Présence sonore terminée.\n")
                    presence_detectee = False

        time.sleep(REFRESH)

except KeyboardInterrupt:
    print("\nArrêt du programme.")
