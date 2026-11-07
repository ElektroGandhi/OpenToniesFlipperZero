#!/usr/bin/env python3
"""SD-Karte des Flippers gegen die lokale Sammlung abgleichen.

Vergleicht wirklich mit dem Gerät, nicht mit einer Merkliste:

    python3 tools/update_tonies.py --alle   # Spiegel in tools/tonies_repo/ holen
    python3 tools/gen_library.py            # Bild-URLs und Namen
    python3 tools/sd_abgleich.py            # zeigt nur den Plan
    python3 tools/sd_abgleich.py --ausfuehren

Was passiert:
  * Umbenannte Dumps (die Sammlung ersetzte `+` durch `&`) werden auf der SD
    umbenannt, aber nur, wenn der Inhalt identisch ist. Verglichen werden die
    Zeilen, denn die Zeilenenden unterscheiden sich; `Lock EAS` zählt nicht, das
    korrigiert die Sammlung nachträglich. So entstehen keine Dubletten.
  * Fehlende Dumps, Bilder und Serienbilder werden kopiert.
  * durations.txt wird aktualisiert.
  * Es wird nichts gelöscht. Was nur auf der SD liegt, bleibt dort und wird genannt.
"""
import argparse, os, re, subprocess, sys, time
import serial

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LAGER = os.path.join(HERE, "tonies_repo")
DURATIONS = os.path.join(HERE, "durations.txt")
NFC = "/ext/nfc/Toniebox Figuren"
DATA = "/ext/apps_data/toniekids"
ICONS = DATA + "/icons_p"
STORAGE = os.path.expanduser("~/.ufbt/current/scripts/storage.py")


class Flipper:
    def __init__(self, port):
        self.s = serial.Serial(port, 230400, timeout=1)
        self.s.write(b"\r\n")
        time.sleep(0.3)
        self.s.read(8192)

    def cli(self, befehl, frist=30):
        self.s.write(befehl.encode() + b"\r\n")
        aus, t = b"", time.time()
        while time.time() - t < frist:
            if self.s.in_waiting:
                aus += self.s.read(self.s.in_waiting)
                if aus.rstrip().endswith(b">:"):
                    break
            else:
                time.sleep(0.02)
        else:
            raise TimeoutError(befehl)
        return aus.decode("utf-8", "replace")

    def baum(self, pfad, prefix=""):
        """Alle Dateien unter pfad, rekursiv, relativ."""
        ergebnis = []
        for z in self.cli(f'storage list "{pfad}"').splitlines():
            m = re.match(r"\s*\[(D|F)\] (.*?)(?: \d+b)?$", z)
            if not m:
                continue
            rel = prefix + m[2]
            if m[1] == "D":
                ergebnis += self.baum(f"{pfad}/{m[2]}", rel + "/")
            else:
                ergebnis.append(rel)
        return ergebnis

    def zeilen(self, pfad):
        """Dateiinhalt als Zeilen, ohne Echo, Größenangabe und Eingabeaufforderung."""
        aus = self.cli(f'storage read "{pfad}"').splitlines()
        return [z.strip() for z in aus[2:] if z.strip() and z.strip() != ">:"]

    def mv(self, a, b):
        # Die Firmware meldet "Storage error: ..."; auf "Error" allein prüfen schlägt nie an.
        return "error" not in self.cli(f'storage rename "{a}" "{b}"').lower()

    def gibt_es(self, pfad):
        return "error" not in self.cli(f'storage stat "{pfad}"').lower()

    def schliessen(self):
        self.s.close()


def zeilen_lokal(pfad):
    with open(pfad, encoding="utf-8", errors="replace") as f:
        return [z.strip() for z in f.read().splitlines() if z.strip()]


def sende(port, lokal, ziel):
    r = subprocess.run([sys.executable, STORAGE, "-p", port, "send", lokal, ziel], capture_output=True)
    if r.returncode:
        print("  FEHLER", ziel, r.stderr.decode("utf-8", "replace").strip()[:160])
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--ausfuehren", action="store_true", help="wirklich schreiben; ohne nur den Plan zeigen")
    a = ap.parse_args()

    lokal = sorted(os.path.relpath(os.path.join(w, f), LAGER)
                   for w, _, fs in os.walk(LAGER) for f in fs if f.endswith(".nfc"))
    fl = Flipper(a.port)
    sd_nfc = [r for r in fl.baum(NFC) if r.endswith(".nfc")]
    sd_icons = set(fl.baum(ICONS))

    # Umbenennungen erkennen: gleicher Pfad bis auf + und &, gleicher Inhalt.
    norm = lambda r: re.sub(r"\s*[+&]\s*", "&", r)
    nur_sd = sorted(set(sd_nfc) - set(lokal))
    fehlt = sorted(set(lokal) - set(sd_nfc))
    je_norm = {norm(r): r for r in fehlt}
    umbenennen = []
    for alt in nur_sd:
        neu = je_norm.get(norm(alt))
        if not neu:
            continue
        # "Lock EAS" korrigiert die Sammlung nachträglich; die Figur bleibt dieselbe.
        ohne = lambda zs: [z for z in zs if not z.startswith("Lock EAS")]
        sd_z, lo_z = fl.zeilen(f"{NFC}/{alt}"), zeilen_lokal(os.path.join(LAGER, neu))
        if ohne(sd_z) == ohne(lo_z):
            umbenennen.append((alt, neu))
            if sd_z == lo_z:
                fehlt.remove(neu)  # sonst danach mit der aktuellen Fassung überschreiben
    bleibt = sorted(set(nur_sd) - {x for x, _ in umbenennen})

    print(f"SD: {len(sd_nfc)} Dumps | lokal: {len(lokal)}")
    print(f"Umbenennen: {len(umbenennen)} | Neu kopieren: {len(fehlt)} | Bleibt, nur auf SD: {len(bleibt)}")
    for x in bleibt:
        print("  nur SD:", x)

    # Bilder: alles, was auf der SD fehlt, nach allen Umbenennungen.
    alt_icons = [(x[:-4] + ".fxbm", n[:-4] + ".fxbm") for x, n in umbenennen if x[:-4] + ".fxbm" in sd_icons]
    ziel_icons = (sd_icons - {x for x, _ in alt_icons}) | {n for _, n in alt_icons}
    icons_neu = [r for r in lokal if r[:-4] + ".fxbm" not in ziel_icons]
    print(f"Bilder neu: {len(icons_neu)}")
    if not a.ausfuehren:
        fl.schliessen()
        print("\nNur der Plan. Schreiben mit --ausfuehren.")
        return 0

    for x, n in umbenennen:
        print(" ", "OK " if fl.mv(f"{NFC}/{x}", f"{NFC}/{n}") else "FEHLER", x, "->", n)
    for x, n in alt_icons:
        fl.mv(f"{ICONS}/{x}", f"{ICONS}/{n}")
    fl.schliessen()  # storage.py braucht die Schnittstelle für sich

    import gen4
    urls, ok, ersatz, serienbild, sendefehler = gen4.bild_urls(), 0, 0, {}, 0
    for rel in icons_neu:
        data, echt = gen4.icon_fuer(rel, urls)
        ok, ersatz = ok + echt, ersatz + (not echt)
        pfad = gen4.schreibe(rel, data)
        sendefehler += not sende(a.port, pfad, f"{ICONS}/{rel[:-4]}.fxbm")
        serie = rel.split("/")[0]
        if echt:
            serienbild.setdefault(serie, data)
    print(f"Bilder: {ok} aus Bildquelle, {ersatz} Ersatzbild mit Initialen")
    for serie in sorted({r.split('/')[0] for r in icons_neu}):
        if f"{serie}/_series.fxbm" in sd_icons:
            continue
        data = serienbild.get(serie) or gen4.fallback(serie)
        pfad = gen4.schreibe(f"{serie}/_series.nfc", data)
        sendefehler += not sende(a.port, pfad, f"{ICONS}/{serie}/_series.fxbm")

    fehler = sendefehler + sum(not sende(a.port, os.path.join(LAGER, r), f"{NFC}/{r}") for r in fehlt)
    print(f"Dumps und Bilder: {fehler} Fehler; {len(fehlt)} Dumps zu kopieren")
    if os.path.exists(DURATIONS) and not sende(a.port, DURATIONS, f"{DATA}/durations.txt"):
        fehler += 1
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
