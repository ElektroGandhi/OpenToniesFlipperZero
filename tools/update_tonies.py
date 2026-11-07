#!/usr/bin/env python3
"""Neue Tonie-Dumps aus der Gemeinschaftssammlung holen und aufs Geraet bringen.

Quelle: https://github.com/nortakales/flipper-zero-tonies  (Ordner `German/`,
Struktur `<Serie>/<Folge>.nfc` — exakt die Struktur, die die App auf dem Flipper
unter `/ext/nfc/Toniebox Figuren/` erwartet).

Geladen wird der **Tarball** des Branches, nicht Datei fuer Datei: ein einziger
Abruf statt Hunderter, und die GitHub-API-Grenze fuer nicht angemeldete Zugriffe
(60 Abrufe je Stunde) wird gar nicht erst beruehrt.

    python3 tools/update_tonies.py                 # holt und legt neu ab (unter tools/tonies_repo/); pusht nichts
    python3 tools/update_tonies.py --sprache French
    python3 tools/update_tonies.py --push          # Neues auf den Flipper kopieren
    python3 tools/update_tonies.py --push --trocken   # zeigt beim Push nur, was passieren wuerde

⚠️ Die Dumps sind Fremdmaterial und werden NICHT committet (`.gitignore`: `*.nfc`).
Dieses Werkzeug wird committet, sein Ergebnis nicht — dieselbe Logik wie bei
`gen_library.py` und `tonies.json`.

Nach einem Update gehoert `python3 tools/gen_library.py` hinterher, sonst kennt
die Handy-Bibliothek die neuen Folgen nicht.
"""
import argparse, io, json, os, subprocess, sys, tarfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STAGE = os.path.join(HERE, "tonies_repo")          # gitignored
MATCHES = os.path.join(HERE, "matches.json")
TARBALL = "https://codeload.github.com/nortakales/flipper-zero-tonies/tar.gz/refs/heads/master"
FLIPPER_DIR = "/ext/nfc/Toniebox Figuren"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def hole_tarball():
    req = urllib.request.Request(TARBALL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def entpacke(raw, sprache):
    """Alle .nfc unterhalb von <sprache>/ -> {"<Serie>/<Folge>.nfc": bytes}."""
    out = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for m in tf.getmembers():
            if not m.isfile() or not m.name.endswith(".nfc"):
                continue
            teile = m.name.split("/")
            # <repo>-<branch>/<Sprache>/<Serie>/<Folge>.nfc
            if len(teile) < 4 or teile[1] != sprache:
                continue
            rel = "/".join(teile[2:])
            f = tf.extractfile(m)
            if f:
                out[rel] = f.read()
    return out


def bekannter_bestand():
    """Was die eigene Sammlung schon kennt: aus matches.json UND aus dem
    Zwischenlager tools/tonies_repo/.

    Ohne die zweite Quelle meldet ein zweiter Lauf hintereinander dieselben
    Dumps als „NEU", weil matches.json von keinem Werkzeug fortgeschrieben
    wird — dieselbe Falle, an der die Kette update_tonies -> gen_library
    ins Leere lief."""
    aus = set()
    if os.path.exists(MATCHES):
        aus.update(json.load(open(MATCHES)))
    if os.path.isdir(STAGE):
        for wurzel, _, dateien in os.walk(STAGE):
            for fn_ in dateien:
                if fn_.endswith(".nfc"):
                    aus.add(os.path.relpath(os.path.join(wurzel, fn_), STAGE))
    return aus


def flipper_da():
    return any(os.path.exists(p) for p in ("/dev/ttyACM0", "/dev/ttyACM1"))


def storage_py():
    p = os.path.expanduser("~/.ufbt/current/scripts/storage.py")
    return p if os.path.exists(p) else None


def push(neu, trocken):
    """Neue Dumps per storage.py auf den Flipper schieben."""
    sp = storage_py()
    if not sp:
        print("  storage.py nicht gefunden (~/.ufbt/current/scripts/storage.py) — kein Push.")
        return 0
    if not flipper_da():
        print("  Kein Flipper an /dev/ttyACM* — kein Push.")
        return 0
    n = 0
    for rel in sorted(neu):
        lokal = os.path.join(STAGE, rel)
        ziel = f"{FLIPPER_DIR}/{rel}"
        if trocken:
            print(f"  [trocken] {ziel}")
            n += 1
            continue
        # storage.py send legt fehlende Elternverzeichnisse selbst an
        # (FlipperStorageOperations.recursive_send -> mkpath) — ein eigener
        # mkdir-Aufruf davor war eine zweite Flipper-Sitzung pro Datei.
        r = subprocess.run([sys.executable, sp, "send", lokal, ziel], capture_output=True)
        if r.returncode == 0:
            n += 1
        else:
            print(f"  FEHLER {rel}: {r.stderr.decode('utf-8', 'replace').strip()[:120]}")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sprache", default="German", choices=["German", "English", "French"])
    ap.add_argument("--push", action="store_true", help="Neues auf den Flipper kopieren")
    ap.add_argument("--trocken", action="store_true", help="beim Push nur zeigen, nichts schreiben (wirkt nur mit --push)")
    ap.add_argument("--alle", action="store_true",
                    help="alles ablegen, nicht nur das Neue (voller Spiegel)")
    args = ap.parse_args()
    if args.trocken and not args.push:
        print("Hinweis: --trocken wirkt nur mit --push; ohne --push wird es ignoriert.")

    print(f"Sammlung laden ({args.sprache}) ...", flush=True)
    dateien = entpacke(hole_tarball(), args.sprache)
    print(f"  im Repo: {len(dateien)} Dumps")

    bekannt = bekannter_bestand()
    print(f"  eigene Sammlung kennt: {len(bekannt)}")
    neu = sorted(set(dateien) - bekannt) if not args.alle else sorted(dateien)
    print(f"  NEU: {len(neu)}")
    if not neu:
        print("\nNichts zu tun — die Sammlung ist auf dem Stand des Repos.")
        return

    os.makedirs(STAGE, exist_ok=True)
    for rel in neu:
        ziel = os.path.join(STAGE, rel)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel, "wb") as f:
            f.write(dateien[rel])

    serien = sorted({r.split("/")[0] for r in neu})
    print(f"\nAbgelegt unter {STAGE}")
    print(f"Betroffene Serien ({len(serien)}):")
    for s in serien[:25]:
        print(f"   {s}")
    if len(serien) > 25:
        print(f"   … und {len(serien)-25} weitere")

    if args.push:
        print("\nAuf den Flipper kopieren ...")
        n = push(neu, args.trocken)
        print(f"  {n}/{len(neu)} uebertragen")
    else:
        print("\nZum Uebertragen: --push (Flipper per USB anstecken)")
    print("Danach: python3 tools/gen_library.py  — sonst kennt die Handy-Bibliothek"
          " die neuen Folgen nicht.")


if __name__ == "__main__":
    main()
