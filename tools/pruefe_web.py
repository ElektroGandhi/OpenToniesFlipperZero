#!/usr/bin/env python3
"""Die Web-App nachmessen — ein Befehl, alle Prüfungen.

    python3 tools/pruefe_web.py            # messen + Screenshots
    python3 tools/pruefe_web.py --nur-zahlen

Prüft bei 375 px Gerätebreite:
  * waagerechtes Scrollen (auf einem Telefon immer ein Fehler)
  * Tippziele gegen die Kindergrenze (SOLL_TAP, s. u.)
  * Anzahl der Schriftgrößen (Deckelung: 3)
  * Kontrast aller Karten- und Knopffarben, hell UND dunkel
  * legt Screenshots in /tmp/opentonies_*.png

⚠️ Die Screenshots danach ANSEHEN. Drei echte Fehler (Überlauf aus der Kachel,
zerfressene Bilder, doppelter Titel) waren in allen Kennzahlen grün und fielen
nur im Bild auf. Eine Geometrieprüfung beantwortet "steht es sich im Weg?",
nie "sieht es richtig aus?".
"""
import glob, shutil
import argparse, http.server, json, os, re, socketserver, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), "web")
PORT = 8899
def _finde_chrome():
    """CHROME aus der Umgebung, sonst ein Chromium von Playwright oder aus dem System."""
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    muster = ["~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
              "/var/cache/ms-playwright/chromium-*/chrome-linux*/chrome"]
    for m in muster:
        treffer = sorted(glob.glob(os.path.expanduser(m)))
        if treffer:
            return treffer[-1]
    return shutil.which("chromium") or shutil.which("google-chrome") or "chromium"


CHROME = _finde_chrome()
SOLL_TAP = 76          # Kindergrenze: Kinder unter 9 verfehlen kleinere Ziele oft


class _Server(socketserver.TCPServer):
    # MUSS als Klassenattribut gesetzt sein: server_bind() liest es waehrend
    # __init__, ein nachtraegliches srv.allow_reuse_address = True kommt zu spaet
    # und der naechste Lauf scheitert mit "Address already in use".
    allow_reuse_address = True


def serve():
    """Die Seite lokal ausliefern. Muss derselbe Ursprung sein wie die Prüfseite,
    sonst ist contentDocument gesperrt und die Messung liefert stumm nichts.
    Rueckgabe: der tatsaechlich benutzte Port."""
    os.chdir(WEB)
    h = http.server.SimpleHTTPRequestHandler
    h.log_message = lambda *a, **k: None
    for port in range(PORT, PORT + 20):
        try:
            srv = _Server(("127.0.0.1", port), h)
        except OSError:
            continue        # belegt (z. B. ein haengengebliebener Lauf) -> naechster
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return port
    print(f"FEHLER: kein freier Port zwischen {PORT} und {PORT+19}")
    sys.exit(1)


def chrome(args, timeout=120):
    if not os.path.exists(CHROME):
        print(f"FEHLER: Chromium nicht unter {CHROME}")
        sys.exit(1)
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox"] + args,
                          capture_output=True, timeout=timeout)


def messen(port):
    r = chrome(["--virtual-time-budget=9000", "--dump-dom",
                f"http://127.0.0.1:{port}/_measure.html?soll={SOLL_TAP}"])
    m = re.search(r"<title>(.*?)</title>", r.stdout.decode("utf-8", "replace"), re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1).replace("&quot;", '"'))
    except Exception:
        return None


def schuss(name, url, groesse="375,812"):
    """Screenshot + eine kleine Fassung daneben.

    Ein 375x812-PNG ist rund 100 kB; ein Leseschutz-Hook in diesem Baum schaetzt
    daraus ~49.000 Token und blockiert das Ansehen — fuer ein kleines Modell ist
    das Bild damit wertlos. Die halbierte JPEG-Fassung liegt bei ~10 kB und
    laesst sich lesen. Zum Beurteilen des Layouts reicht sie.
    """
    ziel = f"/tmp/opentonies_{name}.png"
    chrome([f"--virtual-time-budget=10000", f"--window-size={groesse}",
            f"--screenshot={ziel}", url])
    if not os.path.exists(ziel) or os.path.getsize(ziel) < 5000:
        # Ein Bild unter 5 kB ist mit hoher Wahrscheinlichkeit eine leere Seite
        # oder eine Fehlerseite. Frueher gingen 21 kB grosse 404-Aufnahmen als
        # Erfolg durch — die Groesse ist der zweitgruenlichste Filter neben
        # dem Titel-Test.
        return None, None
    klein = f"/tmp/opentonies_{name}_klein.jpg"
    try:
        from PIL import Image
        im = Image.open(ziel).convert("RGB")
        im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(
            klein, "JPEG", quality=72)
    except Exception:
        klein = None
    return ziel, klein


# ---------- Kontrast ----------
def _lum(h):
    """Relative Leuchtdichte nach WCAG. Alphakanal (#RRGGBBAA / #RGBA) wird
    verworfen — Deckkraft gehoert an die Aufrufstelle, sonst rechnet _lum
    gegen einen Hintergrund, den es nicht kennt."""
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 4:                     # #RGBA -> Alpha verwerfen
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:                     # #RRGGBBAA -> Alpha verwerfen
        h = h[:6]
    elif len(h) != 6:
        raise ValueError(f"unbekannte Farb-Notation: #{h}")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


# ⛔ Bis 12.09.2026 stand "index.html" an vier Stellen fest im Code. Der
# zweite Entwurf (web/index2.html) wurde dadurch NIE gemessen, und das
# Werkzeug schwieg dazu statt zu warnen — ein Messgeraet, das die falsche
# Datei liest, findet nichts und meldet "BESTANDEN".
SEITE = "index.html"      # per --seite umschaltbar, s. main()


def seiten_css():
    """Das CSS der gerade geprueften Seite. EINE Quelle fuer alle Leser."""
    return open(os.path.join(WEB, SEITE), encoding="utf-8").read()


def kontrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def tokens():
    """Farb-Tokens direkt aus der geprueften Seite lesen — nicht abschreiben, sonst driftet es."""
    css = seiten_css()
    hell = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", css.split("@media")[0]))
    dunkel = dict(hell)
    dm = re.search(r"@media \(prefers-color-scheme: dark\)\s*\{(.*?)\n\}", css, re.S)
    if dm:
        dunkel.update(dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", dm.group(1))))
    return hell, dunkel


def _mix(fg, bg, a):
    """Deckkraft ausrechnen. Ein Text mit opacity:.8 hat NICHT den Kontrast
    seiner Farbe — genau daran ging die Nebenzeile auf den Karten durch."""
    def p(h):
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    A, B = p(fg), p(bg)
    return "#%02x%02x%02x" % tuple(round(A[i] * a + B[i] * (1 - a)) for i in range(3))


def nebenzeile():
    """Farbe und Deckkraft von `.card .cnt` aus dem CSS lesen, statt sie
    abzuschreiben — sonst prüft das Werkzeug irgendwann etwas anderes als das,
    was ausgeliefert wird."""
    css = seiten_css()
    m = re.search(r"\.card \.cnt\{([^}]*)\}", css)
    if not m:
        return None, 1.0
    blk = m.group(1)
    var = re.search(r"color:\s*var\((--[\w-]+)\)", blk)
    op = re.search(r"opacity:\s*([\d.]+)", blk)
    return (var.group(1) if var else None), (float(op.group(1)) if op else 1.0)


def buehnentext():
    """Farbe und Deckkraft von `#stage .sr, #stage .st` aus dem CSS lesen.
    Der Wert ist auf allen sechs Buehnenfarben nachzumessen, sonst rutscht
    genau der Satz, der die Ausgraufuehrung erklaert, ohne Warnung unter
    4,5:1 durch (frueher gemessen 2,59:1)."""
    css = seiten_css()
    m = re.search(r"#stage \.sr\s*,\s*#stage \.st\s*\{([^}]*)\}", css)
    if not m:
        return None, 1.0
    blk = m.group(1)
    var = re.search(r"color:\s*var\((--[\w-]+)\)", blk)
    op = re.search(r"opacity:\s*([\d.]+)", blk)
    return (var.group(1) if var else None), (float(op.group(1)) if op else 1.0)


def pruefe_farben():
    hell, dunkel = tokens()
    cnt_var, cnt_op = nebenzeile()
    st_var, st_op = buehnentext()
    fehler = []
    for name, t in (("hell", hell), ("dunkel", dunkel)):
        karten = [t.get(f"--t{i}") for i in range(1, 7)]
        tink = t.get("--tink")
        if tink and all(karten):
            for i, k in enumerate(karten, 1):
                c = kontrast(tink, k)
                if c < 4.5:
                    fehler.append(f"{name}: Text auf Karte t{i} nur {c:.2f}:1 (Soll 4.5)")
            # Die Nebenzeile ("5 Folgen") — mit ihrer echten Deckkraft.
            if cnt_var and t.get(cnt_var):
                for i, k in enumerate(karten, 1):
                    c = kontrast(_mix(t[cnt_var], k, cnt_op), k)
                    if c < 4.5:
                        fehler.append(
                            f"{name}: Nebenzeile auf Karte t{i} nur {c:.2f}:1 (Soll 4.5)")
            # #stage .sr / .st — Buehnennebentext auf allen sechs Kartenfarben.
            # Frueher 2,59:1, weil color:var(--ink2) unbemerkt --tink ueberschrieb.
            if st_var and t.get(st_var):
                for i, k in enumerate(karten, 1):
                    c = kontrast(_mix(t[st_var], k, st_op), k)
                    if c < 4.5:
                        fehler.append(
                            f"{name}: Buehnentext auf Karte t{i} nur {c:.2f}:1 (Soll 4.5)")
            herz = t.get("--heart")
            if herz:
                c = min(kontrast(herz, k) for k in karten)
                if c < 3.0:
                    fehler.append(f"{name}: Herz auf hellster Karte nur {c:.2f}:1 (Soll 3.0)")
        if t.get("--warn") and t.get("--warn-ink"):
            c = kontrast(t["--warn"], t["--warn-ink"])
            if c < 4.5:
                fehler.append(f"{name}: Stopp-Knopf nur {c:.2f}:1 (Soll 4.5)")
        # Abspielen-Knopf — bisher nicht gemessen, obwohl er tagsueber bei
        # 3,74:1 lag (WCAG-Fehler fuer den Fliess-Schriftgrad auf dem Knopf).
        if t.get("--accent") and t.get("--accent-ink"):
            c = kontrast(t["--accent"], t["--accent-ink"])
            if c < 4.5:
                fehler.append(f"{name}: Abspielen-Knopf nur {c:.2f}:1 (Soll 4.5)")
    return fehler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nur-zahlen", action="store_true")
    ap.add_argument("--seite", default="index.html",
                    help="zu pruefende Seite in web/ (z. B. index2.html)")
    args = ap.parse_args()

    global SEITE
    SEITE = args.seite
    # ⚠️ Lieber hier abbrechen als spaeter "BESTANDEN" fuer eine Datei melden,
    # die es nicht gibt. Ein Tippfehler im Namen waere sonst unsichtbar.
    if not os.path.exists(os.path.join(WEB, SEITE)):
        print(f"FEHLER: web/{SEITE} gibt es nicht.")
        return 1
    print(f"Geprueft wird: web/{SEITE}")

    if not os.path.exists(os.path.join(WEB, "library.json")):
        print("FEHLER: web/library.json fehlt — erst `python3 tools/gen_library.py`")
        sys.exit(1)

    port = serve()
    time.sleep(1)
    print(f"Messe bei 375 px …\n")

    d = messen(port)
    ok = True
    if not d:
        print("  KEINE MESSWERTE — liefen Prüfseite und Zielseite vom selben Server?")
        ok = False
    else:
        breit = d.get("innerWidth")
        print(f"  Fensterbreite      {breit} px" +
              ("" if breit == 375 else "   <-- nicht 375! Chrome klemmt auf 500"))
        ueber = d.get("overflow")
        print(f"  Waagerecht scroll  {'JA — FEHLER' if ueber else 'nein'}")
        ok &= not ueber
        print(f"  Kachel / Bild      {d.get('cardSize')} / {d.get('imgSize')}")
        gr = d.get("fontSizes") or []
        print(f"  Schriftgrößen      {len(gr)} ({', '.join(gr)})")
        klein = [t for t in (d.get("tooSmall") or [])]
        if klein:
            print(f"  Tippziele zu klein {klein}")
            ok = False
        else:
            print(f"  Tippziele          alle >= {d.get('soll', SOLL_TAP)} px")

    print(f"\nFarbkontraste (aus den Tokens in {SEITE}):")
    fehler = pruefe_farben()
    if fehler:
        ok = False
        for f in fehler:
            print(f"  FEHLER  {f}")
    else:
        print("  alle bestanden (Text >= 4.5:1, Nicht-Text >= 3:1)")

    if not args.nur_zahlen:
        print("\nScreenshots:")
        bilder = {}
        for name, url in (("regal", f"http://127.0.0.1:{port}/{SEITE}"),
                          ("regal_lieblinge", f"http://127.0.0.1:{port}/_held.html"),
                          ("buehne_hell", f"http://127.0.0.1:{port}/_stage.html"),
                          ("buehne_dunkel", f"http://127.0.0.1:{port}/_stage.html?dark=1")):
            gross, klein = schuss(name, url)
            if not gross:
                print(f"  FEHLGESCHLAGEN: {name}   (leere Seite oder 404?)")
                ok = False
            else:
                print(f"  {klein or gross}" + (f"   (voll: {gross})" if klein else ""))
                bilder[name] = gross
        # Hell/Dunkel-Gegentest fuer die Buehne: sind die beiden PNGs bitweise
        # gleich, hat der /dark/-Test nicht gegriffen — das ist genau der Fehler,
        # der frueher stumm durchging (der Dunkelmodus-Block war umgeschrieben,
        # aber das Werkzeug hat das nicht bemerkt).
        h, d = bilder.get("buehne_hell"), bilder.get("buehne_dunkel")
        if h and d:
            try:
                if open(h, "rb").read() == open(d, "rb").read():
                    print("  FEHLER: buehne_hell und buehne_dunkel sind bitweise gleich"
                          " — der Dunkelmodus greift nicht.")
                    ok = False
            except OSError:
                pass
        print("\n⚠️ Die Bilder jetzt ANSEHEN — die kleinen JPEGs, die grossen PNGs")
        print("   blockiert der Leseschutz. Die Zahlen oben finden keinen einzigen")
        print("   Gestaltungsfehler — sie finden nur Geometrie.")

    print(f"\n{'BESTANDEN' if ok else 'DURCHGEFALLEN'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    # ⛔ KORRIGIERT 12.09.2026: hier stand nur `main()`. Der Rueckgabewert ging
    # damit verloren — das Werkzeug beendete sich IMMER mit 0, auch bei
    # "DURCHGEFALLEN" und bei fehlender Datei. Der eigene Docstring versprach
    # "Beendet mit 0 = bestanden, 1 = durchgefallen"; in einer CI haette die
    # Pruefung stillschweigend nie gegriffen. Am Fehlerfall gemessen.
    sys.exit(main())
