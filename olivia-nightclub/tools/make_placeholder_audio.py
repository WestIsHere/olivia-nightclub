"""
Génère des sons PLACEHOLDER (synthèse pure, stdlib uniquement) pour le développement.

    python tools/make_placeholder_audio.py

Aucun contenu protégé : tout est synthétisé (sinus, bruit, enveloppes).
Les vrais extraits d'artistes doivent être déposés dans web/audio/showcases/<artiste>/
(voir le README.txt de chaque dossier). Tant qu'un dossier d'artiste est vide,
le jeu utilise web/audio/showcases/_placeholder/.
"""

import math
import os
import random
import struct
import unicodedata
import wave

SR = 22050
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "audio")
rnd = random.Random(7)


# ------------------------------------------------------------------ utilitaires

def silence(seconds):
    return [0.0] * int(SR * seconds)


def add(buf, other, at=0.0, gain=1.0):
    start = int(at * SR)
    for i, v in enumerate(other):
        j = start + i
        if j >= len(buf):
            break
        buf[j] += v * gain
    return buf


def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1):
    out = []
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    S = max(0, n - A - D - R)
    for i in range(n):
        if i < A:
            out.append(i / max(1, A))
        elif i < A + D:
            out.append(1 - (1 - s) * (i - A) / max(1, D))
        elif i < A + D + S:
            out.append(s)
        else:
            out.append(s * (1 - (i - A - D - S) / max(1, R)))
    return out


def tone(freq, seconds, wave_kind="sine", a=0.01, d=0.05, s=0.7, r=0.1, detune=0.0):
    n = int(SR * seconds)
    env = env_adsr(n, a, d, s, r)
    out = []
    phase = 0.0
    for i in range(n):
        f = freq * (1 + detune * math.sin(i / SR * 5))
        phase += 2 * math.pi * f / SR
        if wave_kind == "sine":
            v = math.sin(phase)
        elif wave_kind == "square":
            v = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave_kind == "saw":
            v = 2 * ((phase / (2 * math.pi)) % 1) - 1
        else:
            v = math.sin(phase) * 0.7 + math.sin(phase * 2) * 0.3
        out.append(v * env[i])
    return out


def sweep(f0, f1, seconds, kind="sine"):
    n = int(SR * seconds)
    out, phase = [], 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * i / n
        phase += 2 * math.pi * f / SR
        v = math.sin(phase) if kind == "sine" else (1.0 if math.sin(phase) >= 0 else -1.0)
        out.append(v * (1 - i / n))
    return out


def noise(seconds, lowpass=0.0):
    n = int(SR * seconds)
    out, y = [], 0.0
    for _ in range(n):
        x = rnd.uniform(-1, 1)
        y = y + lowpass * (x - y) if lowpass else x
        out.append(y)
    return out


def kick(seconds=0.35):
    n = int(SR * seconds)
    out, phase = [], 0.0
    for i in range(n):
        f = 140 * math.exp(-i / SR * 18) + 45
        phase += 2 * math.pi * f / SR
        out.append(math.sin(phase) * math.exp(-i / SR * 9))
    return out


def hat(seconds=0.06):
    n = int(SR * seconds)
    return [rnd.uniform(-1, 1) * math.exp(-i / SR * 70) * 0.5 for i in range(n)]


def lowpass(buf, k):
    out, y = [], 0.0
    for x in buf:
        y = y + k * (x - y)
        out.append(y)
    return out


def normalize(buf, peak=0.85):
    m = max(1e-6, max(abs(v) for v in buf))
    return [v / m * peak for v in buf]


def write(path, buf, peak=0.85):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    buf = normalize(buf, peak)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in buf))
    print("  écrit", os.path.relpath(path, BASE), f"({len(buf) / SR:.1f} s)")


NOTE = {"A2": 110.0, "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.0, "A3": 220.0,
        "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.0, "A4": 440.0, "C5": 523.25, "E5": 659.25, "G5": 783.99, "A5": 880.0}


# ------------------------------------------------------------------ sons

def robbery(variant):
    buf = silence(3.6)
    # impact grave
    add(buf, kick(0.6), 0.0, 1.2)
    add(buf, noise(0.25, 0.4), 0.0, 0.5)
    # sirène deux tons
    for i in range(6):
        f = (620, 820) if variant == 1 else (540, 760)
        add(buf, tone(f[i % 2], 0.28, "square", a=0.005, d=0.02, s=0.8, r=0.05), 0.35 + i * 0.3, 0.16)
    # balayage montant / descendant
    if variant == 1:
        add(buf, sweep(200, 1400, 0.9), 0.4, 0.25)
        add(buf, sweep(1400, 200, 0.9), 1.4, 0.25)
    else:
        add(buf, sweep(120, 900, 1.6), 0.3, 0.3)
        add(buf, kick(0.4), 2.2, 1.0)
        add(buf, kick(0.4), 2.6, 1.0)
    # impacts finaux
    add(buf, kick(0.5), 3.0, 1.1)
    add(buf, noise(0.4, 0.3), 3.0, 0.4)
    return buf


def showcase(bpm, root, pattern, seconds=12.0):
    buf = silence(seconds)
    beat = 60.0 / bpm
    t = 0.0
    step = 0
    while t < seconds - 0.1:
        if step % 4 == 0 or (step % 8 == 6):
            add(buf, kick(), t, 1.0)
        if step % 2 == 1:
            add(buf, hat(), t, 0.35)
        # basse
        bass_note = NOTE[pattern[(step // 2) % len(pattern)]] / 2
        add(buf, tone(bass_note, beat * 0.9, "saw", a=0.005, d=0.1, s=0.5, r=0.05), t, 0.28)
        # nappe / lead toutes les 2 mesures
        if step % 8 == 0:
            for k, nm in enumerate(pattern[:3]):
                add(buf, tone(NOTE[nm] * 2, beat * 1.6, "sine", a=0.05, d=0.2, s=0.5, r=0.4, detune=0.004), t + k * beat * 0.5, 0.12)
        t += beat / 2
        step += 1
    # foule
    add(buf, lowpass(noise(seconds), 0.08), 0.0, 0.35)
    # fondu de fin
    n = len(buf)
    for i in range(int(SR * 0.6)):
        buf[n - 1 - i] *= i / (SR * 0.6)
    return buf


def ambient(seconds=12.0):
    buf = silence(seconds)
    beat = 60.0 / 122
    t = 0.0
    while t < seconds:
        add(buf, lowpass(kick(0.3), 0.15), t, 0.6)   # kick étouffé (à travers les murs)
        t += beat
    add(buf, lowpass(noise(seconds), 0.05), 0.0, 0.5)   # brouhaha
    for k, nm in enumerate(["A2", "E3", "A3", "C4"]):
        add(buf, tone(NOTE[nm], seconds, "sine", a=1.0, d=0.5, s=0.6, r=1.5, detune=0.003), 0.0, 0.10)
    return buf


def notify():
    buf = silence(0.45)
    add(buf, tone(NOTE["E5"], 0.18, "sine", a=0.005, d=0.05, s=0.6, r=0.1), 0.0, 0.6)
    add(buf, tone(NOTE["A5"], 0.25, "sine", a=0.005, d=0.05, s=0.6, r=0.15), 0.12, 0.6)
    return buf


def cash():
    buf = silence(0.7)
    for i, nm in enumerate(["C5", "E5", "G5", "A5"]):
        add(buf, tone(NOTE[nm], 0.22, "tri", a=0.003, d=0.05, s=0.5, r=0.12), i * 0.09, 0.5)
    add(buf, tone(NOTE["A5"] * 2, 0.3, "sine", a=0.003, d=0.1, s=0.3, r=0.15), 0.36, 0.25)
    return buf


def levelup():
    buf = silence(1.4)
    for i, nm in enumerate(["C4", "E4", "G4", "C5", "E5", "G5"]):
        add(buf, tone(NOTE[nm], 0.5, "tri", a=0.01, d=0.1, s=0.6, r=0.3), i * 0.12, 0.45)
    add(buf, tone(NOTE["C5"] * 2, 0.8, "sine", a=0.05, d=0.2, s=0.5, r=0.5), 0.7, 0.3)
    return buf


def combo():
    buf = silence(1.2)
    add(buf, kick(0.5), 0.0, 1.0)
    add(buf, sweep(300, 2400, 0.5), 0.05, 0.4)
    for i, nm in enumerate(["A4", "C5", "E5", "A5"]):
        add(buf, tone(NOTE[nm], 0.35, "square", a=0.005, d=0.05, s=0.5, r=0.2), 0.3 + i * 0.1, 0.18)
    add(buf, noise(0.5, 0.5), 0.6, 0.3)
    return buf


def click():
    buf = silence(0.06)
    add(buf, tone(1800, 0.05, "sine", a=0.001, d=0.02, s=0.2, r=0.02), 0.0, 0.5)
    return buf


def alert():
    buf = silence(0.9)
    for i in range(3):
        add(buf, tone(880, 0.18, "square", a=0.005, d=0.03, s=0.7, r=0.05), i * 0.28, 0.25)
        add(buf, tone(660, 0.12, "square", a=0.005, d=0.03, s=0.7, r=0.05), i * 0.28 + 0.14, 0.2)
    return buf


def good():
    buf = silence(0.8)
    for i, nm in enumerate(["G4", "C5", "E5"]):
        add(buf, tone(NOTE[nm], 0.4, "sine", a=0.01, d=0.1, s=0.6, r=0.25), i * 0.15, 0.5)
    return buf


def bottle():
    buf = silence(0.6)
    add(buf, noise(0.08, 0.6), 0.0, 0.8)                       # "pop"
    add(buf, sweep(900, 300, 0.12), 0.0, 0.5)
    add(buf, tone(NOTE["E5"], 0.4, "sine", a=0.01, d=0.1, s=0.4, r=0.2), 0.12, 0.35)
    return buf


def slug(name):
    n = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()
    return "".join(c if c.isalnum() else "_" for c in n).strip("_")


ARTISTS = ["Lagui", "Boro 700", "Saisai", "Gims", "PLK", "Leto", "L2B", "La Mano", "Nono la grinta", "Timal",
           "TK", "Niaks", "Le Crime", "3robi", "Mensa", "RnBoi", "Timar", "La Rvfleuse", "Bello&Dallas"]


def main():
    print("Génération des sons placeholder dans", BASE)
    write(os.path.join(BASE, "robbery", "robbery_01.wav"), robbery(1), 0.9)
    write(os.path.join(BASE, "robbery", "robbery_02.wav"), robbery(2), 0.9)
    write(os.path.join(BASE, "showcases", "_placeholder", "showcase_01.wav"), showcase(128, "A", ["A3", "C4", "E4", "G4"]))
    write(os.path.join(BASE, "showcases", "_placeholder", "showcase_02.wav"), showcase(140, "D", ["D3", "F3", "A3", "C4"]))
    write(os.path.join(BASE, "showcases", "_placeholder", "showcase_03.wav"), showcase(112, "E", ["E3", "G3", "A3", "E4"]))
    write(os.path.join(BASE, "ambient", "club_ambient_01.wav"), ambient(), 0.7)
    write(os.path.join(BASE, "ui", "notify.wav"), notify(), 0.7)
    write(os.path.join(BASE, "ui", "cash.wav"), cash(), 0.7)
    write(os.path.join(BASE, "ui", "levelup.wav"), levelup(), 0.8)
    write(os.path.join(BASE, "ui", "combo.wav"), combo(), 0.85)
    write(os.path.join(BASE, "ui", "click.wav"), click(), 0.4)
    write(os.path.join(BASE, "ui", "bottle.wav"), bottle(), 0.7)
    write(os.path.join(BASE, "events", "alert.wav"), alert(), 0.75)
    write(os.path.join(BASE, "events", "good.wav"), good(), 0.7)
    for artist in ARTISTS:
        folder = os.path.join(BASE, "showcases", slug(artist))
        os.makedirs(folder, exist_ok=True)
        readme = os.path.join(folder, "README.txt")
        if not os.path.exists(readme):
            with open(readme, "w", encoding="utf-8") as f:
                f.write(
                    f"Extraits audio autorisés pour le showcase de {artist}.\n"
                    f"Déposez ici des fichiers .mp3 / .ogg / .wav (5 à 20 s), ex : {slug(artist)}_01.mp3, {slug(artist)}_02.mp3…\n"
                    "Puis Admin → Audio → « Rescanner les assets » (ou redémarrez le serveur).\n"
                    "Tant que ce dossier est vide, le jeu utilise showcases/_placeholder/.\n"
                )
    print("Terminé.")


if __name__ == "__main__":
    main()
