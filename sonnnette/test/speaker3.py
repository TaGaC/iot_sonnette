import RPi.GPIO as GPIO
import time

# --- Configuration GPIO ---
GPIO.setmode(GPIO.BCM)
SPEAKER_PIN = 17  # PWM GPIO
GPIO.setup(SPEAKER_PIN, GPIO.OUT)

pwm = GPIO.PWM(SPEAKER_PIN, 440)  # Initialisation avec La

# --- Dictionnaire des notes ---
NOTES = {
    'E5': 659,
    'D#5': 622,
    'B4': 494,
    'D5': 587,
    'C5': 523,
    'A4': 440,
    'PAUSE': 0
}

# --- Mélodie simplifiée ---
MELODY = [
    ('E5', 0.3), ('D#5', 0.3), ('E5', 0.3), ('D#5', 0.3), 
    ('E5', 0.3), ('B4', 0.3), ('D5', 0.3), ('C5', 0.3),
    ('A4', 0.6),
    ('PAUSE', 0.3),
    ('C4', 0.3), ('E4', 0.3), ('A4', 0.3), ('B4', 0.6),
    ('PAUSE', 0.3),
    ('E4', 0.3), ('G#4', 0.3), ('B4', 0.3), ('C5', 0.6)
]

def play_note(note, duration):
    freq = NOTES.get(note, 0)
    if freq == 0:
        pwm.stop()
    else:
        pwm.ChangeFrequency(freq)
        pwm.start(50)
    time.sleep(duration)
    pwm.stop()
    time.sleep(0.05)

try:
    print("Lecture de la Lettre à Élise 🎵")
    for note, duration in MELODY:
        play_note(note, duration)

finally:
    pwm.stop()
    GPIO.cleanup()
