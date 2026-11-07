#!/usr/bin/env python3
"""Kleine Spieluhr-Melodie für das Video, vollständig synthetisch (eigenes Werk, MIT).

    python3 docs/media/quelle/musik.py ziel.wav [sekunden]
"""
import sys, wave
import numpy as np

RATE = 44100
BPM = 88
SCHLAG = 60 / BPM
# Akkorde je Takt und Melodie in Halbtönen über C4 (None = Pause)
AKKORDE = [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]]
MELODIE = [
    [12, None, 16, 19, 16, None, 12, None], [9, None, 12, 16, 12, None, 9, 7],
    [5, None, 9, 12, 14, 12, 9, None], [7, 11, 14, None, 11, None, 7, None],
    [12, 16, 19, None, 21, 19, 16, None], [9, 12, 16, None, 12, None, 9, None],
    [5, 9, 12, 9, 14, None, 12, None], [7, None, 11, 14, 11, 7, None, None],
]


def ton(halb, dauer, laut=1.0, art="uhr"):
    f = 261.63 * 2 ** (halb / 12)
    t = np.arange(int(RATE * dauer)) / RATE
    if art == "uhr":
        klang = np.sin(2 * np.pi * f * t) * np.exp(-3.2 * t) + 0.4 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-6 * t)
        klang += 0.18 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-22 * t)
    elif art == "bass":
        klang = np.sin(2 * np.pi * f * t) * np.exp(-1.6 * t)
    else:
        klang = np.sin(2 * np.pi * f * t) * np.minimum(t * 3, 1) * np.exp(-0.9 * t) * 0.8
    anschlag = np.minimum(t / 0.004, 1)
    return klang * anschlag * laut


def mischen(spur, signal, start):
    i = int(start * RATE)
    n = min(len(signal), len(spur) - i)
    if n > 0:
        spur[i : i + n] += signal[:n]


def erzeuge(sekunden):
    n = int(RATE * sekunden)
    links, rechts = np.zeros(n), np.zeros(n)
    takt = 0
    while takt * 4 * SCHLAG < sekunden:
        t0 = takt * 4 * SCHLAG
        ak = AKKORDE[takt % 4]
        mischen(links, ton(ak[0] - 12, 4 * SCHLAG, 0.30, "bass"), t0)
        mischen(rechts, ton(ak[0] - 12, 4 * SCHLAG, 0.30, "bass"), t0)
        for h in ak:
            mischen(links, ton(h, 4 * SCHLAG, 0.09, "fla"), t0)
            mischen(rechts, ton(h + 12, 4 * SCHLAG, 0.06, "fla"), t0)
        if takt >= 1:
            for i, h in enumerate(MELODIE[(takt - 1) % 8]):
                if h is None:
                    continue
                s = t0 + i * SCHLAG / 2
                mischen(links, ton(h, 1.4, 0.26), s)
                mischen(rechts, ton(h, 1.4, 0.20), s + 0.012)
        takt += 1
    # kleiner Raum: zwei Echos
    for spur in (links, rechts):
        for tief, laut in ((0.27, 0.22), (0.53, 0.10)):
            d = int(tief * RATE)
            spur[d:] += spur[:-d] * laut
    aus = np.stack([links, rechts], axis=1)
    aus /= np.abs(aus).max() / 0.7
    h = np.ones(n)
    h[: RATE] = np.linspace(0, 1, RATE)
    h[-3 * RATE :] = np.linspace(1, 0, 3 * RATE)
    return aus * h[:, None]


if __name__ == "__main__":
    ziel, sek = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 36
    daten = (erzeuge(sek) * 32767).astype("<i2")
    with wave.open(ziel, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(daten.tobytes())
