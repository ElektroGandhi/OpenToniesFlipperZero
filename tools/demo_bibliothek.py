#!/usr/bin/env python3
"""Demo-Bibliothek: OpenTonies ausprobieren, ganz ohne fremdes Material.

Fünf erfundene Figuren mit eigener Grafik (docs/media/figuren/). Die Dumps sind
Fantasiewerte. Keine Toniebox spielt damit etwas ab, aber Menü, Bilder, Timer
und Bluetooth lassen sich vollständig testen.

    python3 tools/demo_bibliothek.py --bauen     # nach tools/demo/ erzeugen
    python3 tools/demo_bibliothek.py --an        # eigene Sammlung verstecken, Demo aufspielen
    python3 tools/demo_bibliothek.py --aus       # Demo entfernen, Sammlung zurückholen

Die eigene Sammlung wird dabei nur umbenannt, nie gelöscht.
"""
import argparse, json, os, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FIG = os.path.join(HERE, "..", "docs", "media", "figuren")
AUS = os.path.join(HERE, "demo")
NFC = "/ext/nfc/Toniebox Figuren"
VERSTECK = "/ext/nfc/Toniebox Figuren.versteckt"
DATA = "/ext/apps_data/toniekids"
ICONS = DATA + "/icons_p"
ICONS_V = ICONS + ".versteckt"
DATEIEN = ("settings.txt", "favorites.txt", "durations.txt")

# (Serie, Folge, Bild, Minuten, Thema, Beschreibung)
FIGUREN = [
    ("Fuchs Fridolin", "Fuchs Fridolin - Die Laterne im Wald", "fuchs", 42, "Hörspiel",
     "Fridolin findet im Wald eine Laterne, die nur für mutige Füchse leuchtet."),
    ("Fuchs Fridolin", "Fuchs Fridolin - Der verschwundene Mond", "fuchs", 38, "Hörspiel",
     "Wo ist der Mond geblieben? Fridolin macht sich mit einer Leiter auf die Suche."),
    ("Eule Ottilie", "Eule Ottilie - Warum ist die Nacht dunkel", "eule", 55, "Wissen",
     "Ottilie erklärt, was nachts am Himmel passiert und warum Eulen so gut sehen."),
    ("Drache Funke", "Drache Funke - Das kleine Feuer", "drache", 47, "Hörspiel mit Liedern",
     "Funke kann noch kein Feuer spucken, aber dafür wunderbar singen."),
    ("Robo Rudi", "Robo Rudi - Die Schraube im Muesli", "robo", 31, "Hörspiel",
     "Rudi repariert alles. Nur nicht das, was gar nicht kaputt war."),
    ("Igel Ida", "Igel Ida - Lieder fuer den Herbst", "igel", 60, "Musik",
     "Zwölf Lieder zum Mitsingen, für Spaziergänge durch das bunte Laub."),
]


def demo_dump(n):
    """Ein gültiger SLIX-L-Datensatz mit Fantasiewerten (Hersteller-Präfix bleibt, Rest erfunden)."""
    uid = f"E0 04 03 D0 0D 0A 00 {n:02X}"
    block = " ".join(f"{(n * 17 + i) & 0xFF:02X}" for i in range(32))
    return f"""Filetype: Flipper NFC device
Version: 4
Device type: SLIX
UID: {uid}
DSFID: 00
AFI: 00
IC Reference: 03
Lock DSFID: false
Lock AFI: false
Block Count: 8
Block Size: 04
Data Content: {block}
Security Status: 00 00 00 00 00 00 00 00
Capabilities: Default
Password Privacy: 00 00 00 00
Password Destroy: 00 00 00 00
Password EAS: 00 00 00 00
Privacy Mode: false
Lock EAS: false
"""


def bauen():
    import gen4
    os.makedirs(AUS, exist_ok=True)
    zeilen = []
    for i, (serie, folge, bild, minuten, _, _) in enumerate(FIGUREN, 1):
        rel = f"{serie}/{folge}"
        os.makedirs(os.path.join(AUS, "nfc", serie), exist_ok=True)
        os.makedirs(os.path.join(AUS, "icons_p", serie), exist_ok=True)
        with open(os.path.join(AUS, "nfc", rel + ".nfc"), "w") as f:
            f.write(demo_dump(i))
        roh = Image.open(os.path.join(FIG, bild + ".png")).convert("RGBA")
        grund = Image.new("RGBA", roh.size, (255, 255, 255, 255))
        data = gen4.pack(gen4.render_outline(Image.alpha_composite(grund, roh).convert("RGB")))
        for ziel in (rel + ".fxbm", serie + "/_series.fxbm"):
            with open(os.path.join(AUS, "icons_p", ziel), "wb") as f:
                f.write(data)
        zeilen.append(f"{rel}.nfc\t{minuten}\n")
    with open(os.path.join(AUS, "durations.txt"), "w", encoding="utf-8") as f:
        f.writelines(zeilen)
    print("Demo gebaut:", AUS)


def web_bibliothek(ziel):
    """library.json + Bilder für die Web-Demo (GitHub Pages)."""
    os.makedirs(os.path.join(ziel, "img"), exist_ok=True)
    items = []
    for serie, folge, bild, minuten, thema, text in FIGUREN:
        Image.open(os.path.join(FIG, bild + ".png")).convert("RGBA").resize((400, 400)).save(
            os.path.join(ziel, "img", bild + ".webp"), quality=88)
        # Dateinamen bleiben ASCII (wie in der Sammlung), die Anzeige bekommt Umlaute.
        ep = folge.split(" - ", 1)[1].replace("Muesli", "Müsli").replace("fuer", "für")
        items.append({"path": f"{serie}/{folge}.nfc", "series": serie, "episode": ep, "theme": thema,
                      "desc": text, "tracks": [], "minutes": minuten, "img": bild + ".webp",
                      "img_url": None, "url": None, "match": "demo", "tts": None})
    themen = sorted({i["theme"] for i in items})
    with open(os.path.join(ziel, "library.json"), "w", encoding="utf-8") as f:
        json.dump({"generated": "demo", "count": len(items), "themes": themen, "items": items},
                  f, ensure_ascii=False)
    print("Web-Demo:", ziel)


def senden(port, lokal, ziel):
    sp = os.path.expanduser("~/.ufbt/current/scripts/storage.py")
    subprocess.run([sys.executable, sp, "-p", port, "send", lokal, ziel], check=True, capture_output=True)


def an(port):
    import sd_abgleich as sd
    f = sd.Flipper(port)
    # Ein zweites --an würde die Sicherung mit Demo-Daten überschreiben: Rename ersetzt das Ziel.
    if f.gibt_es(VERSTECK):
        f.schliessen()
        print("Demo ist schon aktiv. Erst --aus, nichts geändert.")
        return 1
    for alt, neu in ((NFC, VERSTECK), (ICONS, ICONS_V)):
        if not f.mv(alt, neu):
            f.schliessen()
            print(f"Abbruch: {alt} ließ sich nicht verschieben. Mit --aus prüfen.")
            return 1
    for name in DATEIEN:
        if f.gibt_es(f"{DATA}/{name}"):
            f.mv(f"{DATA}/{name}", f"{DATA}/{name}.versteckt")
    f.schliessen()
    for quelle, ziel in (("nfc", NFC), ("icons_p", ICONS)):
        wurzel_q = os.path.join(AUS, quelle)
        for wurzel, _, dateien in os.walk(wurzel_q):
            for d in dateien:
                p = os.path.join(wurzel, d)
                senden(port, p, f"{ziel}/{os.path.relpath(p, wurzel_q)}")
    senden(port, os.path.join(AUS, "durations.txt"), f"{DATA}/durations.txt")
    print("Demo aktiv. Zurück mit --aus.")
    return 0


def aus(port):
    import sd_abgleich as sd
    f = sd.Flipper(port)
    # Ohne Sicherung gibt es nichts zurückzuholen: dann auch nichts anfassen.
    if not (f.gibt_es(VERSTECK) and f.gibt_es(ICONS_V)):
        f.schliessen()
        print("Keine versteckte Sammlung gefunden, die Demo ist nicht aktiv. Nichts geändert.")
        return 1
    # Nur entfernen, was die Demo selbst angelegt hat.
    for quelle, ziel in (("nfc", NFC), ("icons_p", ICONS)):
        wurzel_q = os.path.join(AUS, quelle)
        for wurzel, _, dateien in os.walk(wurzel_q, topdown=False):
            rel = os.path.relpath(wurzel, wurzel_q)
            for d in dateien:
                f.cli(f'storage remove "{ziel}/{rel}/{d}"')
            f.cli(f'storage remove "{ziel}/{rel}"' if rel != "." else f'storage remove "{ziel}"')
    ok = f.mv(VERSTECK, NFC) and f.mv(ICONS_V, ICONS)
    for name in DATEIEN:
        if f.gibt_es(f"{DATA}/{name}.versteckt"):
            f.cli(f'storage remove "{DATA}/{name}"')
            ok = f.mv(f"{DATA}/{name}.versteckt", f"{DATA}/{name}") and ok
    f.schliessen()
    print("Sammlung zurück." if ok else "⚠️ Zurückholen unvollständig, bitte auf der SD prüfen.")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--bauen", action="store_true")
    g.add_argument("--web", metavar="ZIEL", help="library.json + Bilder für die Web-Demo erzeugen")
    g.add_argument("--an", action="store_true")
    g.add_argument("--aus", action="store_true")
    ap.add_argument("--port", default="/dev/ttyACM0")
    a = ap.parse_args()
    if a.bauen:
        bauen()
    elif a.web:
        web_bibliothek(a.web)
    elif a.an:
        bauen()
        sys.exit(an(a.port))
    else:
        sys.exit(aus(a.port))
