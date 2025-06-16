import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Initialisation I2C
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

# Entrée A0 (remplace par ADS.P1 si tu utilises A1, etc.)
chan = AnalogIn(ads, ADS.P1)

print("Début des mesures sonores : appuie sur Ctrl+C pour arrêter.")

try:
    while True:
        # Affiche la tension (niveau sonore)
        print("Tension mesurée : {:.2f} V | Valeur brute ADC : {}".format(chan.voltage, chan.value))
        time.sleep(0.05)  # 20 mesures/sec
except KeyboardInterrupt:
    print("\nArrêt du programme.")

