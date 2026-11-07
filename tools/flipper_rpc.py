#!/usr/bin/env python3
"""Einen Flipper Zero über USB fernsteuern: Tasten senden, Bildschirm fotografieren.

Spricht das Protobuf-RPC der Firmware direkt und kommt deshalb ohne
Zusatzpaket aus (nur pyserial und Pillow). Damit laufen Gerätetests und
Bildschirmfotos ohne Handarbeit.

    from flipper_rpc import Flipper
    with Flipper() as f:
        f.taste("ok")
        f.foto("bild.png", hochformat=True)
"""
import time

import serial
from PIL import Image

# Feldnummern aus flipperzero-protobuf (flipper.proto, gui.proto)
F_ID, F_STATUS, F_HAS_NEXT = 1, 2, 3
F_START_STREAM, F_STOP_STREAM, F_FRAME, F_INPUT = 20, 21, 22, 23
TASTEN = {"hoch": 0, "runter": 1, "rechts": 2, "links": 3, "ok": 4, "zurueck": 5}
PRESS, RELEASE, SHORT, LONG = 0, 1, 2, 3
BREITE, HOEHE = 128, 64


def _varint(n):
    aus = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        aus.append(b | (0x80 if n else 0))
        if not n:
            return bytes(aus)


def _feld_varint(nr, wert):
    return _varint(nr << 3) + _varint(wert)


def _feld_bytes(nr, daten):
    return _varint(nr << 3 | 2) + _varint(len(daten)) + daten


def _felder(daten):
    """Protobuf-Nachricht in {feldnummer: wert} zerlegen."""
    i, aus = 0, {}
    while i < len(daten):
        kopf, i = _lies_varint(daten, i)
        nr, art = kopf >> 3, kopf & 7
        if art == 0:
            aus[nr], i = _lies_varint(daten, i)
        elif art == 2:
            n, i = _lies_varint(daten, i)
            aus[nr], i = daten[i : i + n], i + n
        else:
            raise ValueError(f"Protobuf-Art {art} nicht unterstützt")
    return aus


def _lies_varint(daten, i):
    wert = schiebe = 0
    while True:
        b = daten[i]
        i += 1
        wert |= (b & 0x7F) << schiebe
        schiebe += 7
        if not b & 0x80:
            return wert, i


class Flipper:
    def __init__(self, port="/dev/ttyACM0"):
        self.s = serial.Serial(port, 230400, timeout=2)
        self.nr = 0
        self.s.write(b"\r\n")
        time.sleep(0.3)
        self.s.reset_input_buffer()
        self.s.write(b"start_rpc_session\r")
        self.s.read_until(b"start_rpc_session\r\n")
        time.sleep(0.2)
        self._senden(_feld_bytes(F_START_STREAM, b""))
        self._bild = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.schliessen()

    def schliessen(self):
        try:
            self._senden(_feld_bytes(F_STOP_STREAM, b""))
            self._senden(_feld_bytes(19, b""))  # stop_session
            time.sleep(0.2)
        finally:
            self.s.close()

    def _senden(self, inhalt):
        self.nr += 1
        nachricht = _feld_varint(F_ID, self.nr) + inhalt
        self.s.write(_varint(len(nachricht)) + nachricht)

    def _lies_nachricht(self):
        laenge = schiebe = 0
        while True:
            b = self.s.read(1)
            if not b:
                raise TimeoutError("keine Antwort vom Flipper")
            laenge |= (b[0] & 0x7F) << schiebe
            schiebe += 7
            if not b[0] & 0x80:
                break
        daten = b""
        while len(daten) < laenge:
            stueck = self.s.read(laenge - len(daten))
            if not stueck:
                raise TimeoutError("Nachricht unvollständig")
            daten += stueck
        return _felder(daten)

    def _pumpen(self, dauer):
        """Eingehende Nachrichten lesen; der jeweils letzte Bildschirm bleibt stehen."""
        ende = time.time() + dauer
        while time.time() < ende:
            if not self.s.in_waiting:
                time.sleep(0.01)
                continue
            n = self._lies_nachricht()
            if F_FRAME in n:
                self._bild = _felder(n[F_FRAME]).get(1)

    def taste(self, name, lang=False, warten=0.35):
        taste = TASTEN[name]

        def ereignis(art):
            self._senden(_feld_bytes(F_INPUT, _feld_varint(1, taste) + _feld_varint(2, art)))

        ereignis(PRESS)
        if lang:
            self._pumpen(0.6)
            ereignis(LONG)
            self._pumpen(0.1)
        else:
            ereignis(SHORT)
        ereignis(RELEASE)
        self._pumpen(warten)

    def warten(self, sekunden):
        self._pumpen(sekunden)

    def bild(self, hochformat=True):
        """Aktueller Bildschirm als PIL-Bild im Modus "1" (0 = schwarz)."""
        self._pumpen(0.3)
        if not self._bild:
            raise RuntimeError("noch kein Bildschirm empfangen")
        roh = self._bild
        img = Image.new("1", (BREITE, HOEHE), 1)
        px = img.load()
        for y in range(HOEHE):
            for x in range(BREITE):
                if roh[(y // 8) * BREITE + x] >> (y % 8) & 1:
                    px[x, y] = 0
        # Die App zeichnet im Hochformat; der Rahmen kommt um 90 Grad gedreht an.
        return img.transpose(Image.ROTATE_270) if hochformat else img

    def foto(self, pfad, hochformat=True, zoom=4):
        img = self.bild(hochformat)
        img.resize((img.width * zoom, img.height * zoom), Image.NEAREST).save(pfad)
        return img
