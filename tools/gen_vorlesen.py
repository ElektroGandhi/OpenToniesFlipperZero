#!/usr/bin/env python3
"""Beschreibungen vorlesen lassen: web/tts/*.mp3 mit Piper erzeugen.

WARUM VORPRODUZIERT UND NICHT LIVE
Piper (Adresse: Umgebungsvariable `PIPER_HOST`) spricht **Wyoming** — ein binaeres TCP-Protokoll
auf Port 10200, kein HTTP. Ein Browser kann das nicht, und die Web-App laeuft
ohnehin ueber HTTPS (ein Aufruf nach `http://` waere Mixed Content). Deshalb
werden die Dateien einmal erzeugt und neben den Bildern ausgeliefert. Das ist
auch im Betrieb besser: kein Warten, und es funktioniert, wenn Piper aus ist.

⚠️ DAS WYOMING-FORMAT HAT ZWEI LAENGENFELDER.
Eine Nachricht besteht aus Kopfzeile, dann `data_length` Bytes JSON, dann
`payload_length` Bytes Nutzlast:

    {"type":"audio-chunk","data_length":61,"payload_length":2048}\\n
    {"rate":22050,"width":2,"channels":1,...}       <- data_length Bytes
    <2048 Bytes PCM>                                <- payload_length Bytes

Wer `data_length` ignoriert, laeuft im Offset dauerhaft falsch und sieht
Binaermuell statt JSON. Genau daran ist am 12.09.2026 eine Fehldiagnose
entstanden: Der Dienst galt als kaputt ("liefert kein Audio"), obwohl er
einwandfrei arbeitete — der Fehler sass im Leser.

⚠️ ZURUECKGENOMMEN: Hier stand, `{"type":"describe"}` antworte mit einem
LEEREN Objekt. **Das ist falsch.** Gemessen am 12.09.2026 liefert `describe`
ein volles `info`-Objekt: 7 Schluessel, `piper` 2.4.3, **164 Stimmen**,
`frank_v8` enthalten. Leer sieht es nur, wer `data_length` ignoriert — also
genau der Leserfehler von oben. Die Falschaussage war die Fehldiagnose, die
sich selbst bestaetigt hat: kaputter Leser -> "leeres describe" -> "Dienst
defekt". Ein Messgeraet, das nichts findet, ist damit nicht bewiesen.

Aufruf:
    python3 tools/gen_vorlesen.py                # alles Fehlende erzeugen
    python3 tools/gen_vorlesen.py --limit 3      # erst einmal probieren
    python3 tools/gen_vorlesen.py --neu          # auch Vorhandenes ueberschreiben
    python3 tools/gen_vorlesen.py --nur-index    # nur verknuepfen, Piper bleibt aus

Ergebnis: web/tts/<sha1>.mp3 + das Feld `tts` in web/library.json.
web/tts/ ist gitignored — erzeugt, nicht committet.
"""
import argparse, hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time, wave

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
WEB = os.path.join(WURZEL, "web")
LIB = os.path.join(WEB, "library.json")
TTS = os.path.join(WEB, "tts")

PIPER_HOST = os.environ.get("PIPER_HOST", "127.0.0.1")
PIPER_PORT = 10200
MP3_BITRATE = "48k"          # Sprache mono — darueber wird nur die Datei groesser


def lese_wyoming(sock, timeout=90):
    """Nachrichten als (typ, data, nutzlast) liefern. Beachtet BEIDE Laengen."""
    sock.settimeout(timeout)
    buf = b""
    while True:
        while b"\n" not in buf:
            d = sock.recv(65536)
            if not d:
                return
            buf += d
        zeile, buf = buf.split(b"\n", 1)
        try:
            kopf = json.loads(zeile)
        except Exception:
            continue                     # Rahmen verloren: naechste Zeile suchen
        dl = kopf.get("data_length") or 0
        pl = kopf.get("payload_length") or 0
        while len(buf) < dl + pl:
            d = sock.recv(65536)
            if not d:
                break
            buf += d
        data = json.loads(buf[:dl]) if dl else (kopf.get("data") or {})
        nutz = buf[dl:dl + pl]
        buf = buf[dl + pl:]
        yield kopf.get("type"), data, nutz


def sprich(text, timeout=120):
    """Text -> (pcm, rate). Leeres pcm heisst: nichts bekommen."""
    s = socket.create_connection((PIPER_HOST, PIPER_PORT), timeout=20)
    try:
        s.sendall((json.dumps({"type": "synthesize", "data": {"text": text}}) + "\n").encode())
        pcm, rate = b"", 22050
        for typ, data, nutz in lese_wyoming(s, timeout):
            if typ == "audio-start":
                rate = data.get("rate", rate)
            elif typ == "audio-chunk":
                pcm += nutz
                rate = data.get("rate", rate)
            elif typ == "audio-stop":
                break
        return pcm, rate
    finally:
        s.close()


def nach_mp3(pcm, rate, ziel):
    """PCM -> MP3. Ohne ffmpeg bleibt es WAV (grosser, aber brauchbar)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = tmp.name
    try:
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        try:
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", wav,
                 "-c:a", "libmp3lame", "-b:a", MP3_BITRATE, ziel],
                capture_output=True)
        except FileNotFoundError:
            # Der Docstring versprach "ohne ffmpeg bleibt es WAV" — ohne dieses
            # except starb der Lauf stattdessen mitten drin.
            r = None
        if r is not None and r.returncode == 0 and os.path.getsize(ziel) > 500:
            return os.path.basename(ziel)
        # Rueckfall: WAV behalten, damit die Seite trotzdem etwas hat
        wav_ziel = ziel[:-4] + ".wav"
        # os.replace scheitert bei cross-device link (tmpfs -> ext4)
        # -> kopieren + original loeschen
        shutil.copy2(wav, wav_ziel)
        wav = None
        return os.path.basename(wav_ziel)
    finally:
        if wav and os.path.exists(wav):
            os.unlink(wav)


def vorlese_text(it):
    """Muss ZEICHENGLEICH zu `vorleseText()` in web/index.html sein — der
    Dateiname ist sha1 ueber genau diesen Text.

    ⚠️ Frueher filterte dieses Werkzeug nur auf `desc`. Damit bekamen die 298
    Folgen ohne Beschreibung NIE eine Piper-Datei, obwohl die Web-App dort
    bewusst den Namen vorliest — genau fuer nichtlesende Kinder. Sie hingen
    stumm an der Geraetestimme.
    """
    d = (it.get("desc") or "").strip()
    if d:
        return d
    serie = (it.get("series") or "").strip()
    folge = (it.get("episode") or "").strip()
    if serie and folge and serie != folge:
        return f"{serie}. {folge}."
    return folge or serie


def schreibe(doc):
    """library.json atomar schreiben. Wird ZWISCHENDURCH gerufen, nicht nur am
    Ende: Der erste Lauf brach nach 148 von 354 Dateien ab — die MP3s lagen da,
    aber `library.json` kannte nur 3 davon, weil der Index erst zum Schluss
    geschrieben wurde. Die Arbeit war damit unsichtbar.

    ⚠️ NUR die `tts`-Felder werden geschrieben, alles andere kommt frisch von
    der Platte. Grund (gemessen 12.09.2026): Dieses Werkzeug laeuft ~90 Minuten.
    Wer `doc` aus dem Speicher blind zurueckschreibt, verwirft jede Aenderung,
    die `gen_library.py` in der Zwischenzeit gemacht hat — ein klassisches
    Lost Update. Ein Lauf von 11:38 haette so den Stand von 12:24 geloescht.
    """
    try:
        aktuell = json.load(open(LIB, encoding="utf-8"))
    except Exception:
        aktuell = doc                     # Datei weg/zerschossen: eigener Stand
    if aktuell is not doc:
        # `tts` aus unserem Lauf in den frischen Stand heben, ueber `path`
        # (nicht ueber den Listenindex — die Liste kann sich geaendert haben).
        #
        # ⚠️ Der Schluessel ist `path`, weil es das einzige Feld ist, das
        # gefuellt UND eindeutig ist (gemessen: 652/652, 652 eindeutig).
        # Ein `id`-Feld GIBT ES NICHT — ein Merge darueber ergaebe lauter
        # `None`-Schluessel und wuerde jedem Eintrag das `tts` des letzten
        # verpassen. `url` ist nur bei 367 von 652 gefuellt, `episode` hat
        # 20 Doppelnamen. Wer diesen Schluessel aendert, zaehlt vorher nach.
        meine = {it["path"]: it["tts"] for it in doc["items"]
                 if it.get("tts") and it.get("path")}
        for it in aktuell["items"]:
            t = meine.get(it.get("path"))
            if t:
                it["tts"] = t
    tmp = LIB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(aktuell, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LIB)


def nur_index(doc):
    """Vorhandene MP3s neu verknuepfen, ohne Piper zu rufen.

    Wofuer: Nach einem Lauf mit aelterem Code lagen 253 MP3s auf Platte, aber
    `library.json` kannte nur 190 — 63 Dateien waren verwaist und die Seite
    fiel dort stumm auf die Browserstimme zurueck. Der Dateiname ist sha1 des
    Vorlesetexts, also ist die Zuordnung rein rechnerisch nachholbar.
    """
    if not os.path.isdir(TTS):
        print("web/tts/ gibt es nicht — nichts zu verknuepfen.")
        return 0
    da = {f for f in os.listdir(TTS) if f.endswith((".mp3", ".wav"))}
    treffer = fehlt = 0
    for it in doc["items"]:
        text = vorlese_text(it)
        if not text:
            continue
        stamm = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
        for endung in (".mp3", ".wav"):
            if stamm + endung in da:
                it["tts"] = stamm + endung
                treffer += 1
                break
        else:
            fehlt += 1
    schreibe(doc)
    print(f"verknuepft: {treffer} | ohne Datei: {fehlt} | auf Platte: {len(da)}")
    verwaist = len(da) - treffer
    if verwaist > 0:
        print(f"⚠️ {verwaist} Dateien auf Platte, die zu keinem Text passen — "
              "meist aus einem Lauf mit anderem Vorlesetext. Schaden: keiner "
              "(nur Platz). `--neu` erzeugt sie mit dem aktuellen Text neu.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None, help="nur die ersten N erzeugen")
    ap.add_argument("--neu", action="store_true", help="Vorhandenes ueberschreiben")
    ap.add_argument("--nur-index", action="store_true",
                    help="nur vorhandene MP3s verknuepfen, Piper nicht rufen")
    args = ap.parse_args()

    if not os.path.exists(LIB):
        print("FEHLER: web/library.json fehlt — erst `python3 tools/gen_library.py`")
        return 1
    doc = json.load(open(LIB, encoding="utf-8"))
    if args.nur_index:
        return nur_index(doc)

    posten = [it for it in doc["items"] if vorlese_text(it)]
    print(f"Folgen mit Vorlesetext: {len(posten)} von {doc.get('count')}")
    if not posten:
        print("Nichts vorzulesen.")
        return 0

    # Erreichbarkeit an einer ECHTEN Synthese pruefen. `describe` wuerde hier
    # auch gehen (es antwortet, s. Kopf der Datei) — aber es beweist nur, dass
    # der Dienst redet, nicht dass er Audio herausgibt. Die Probe unten prueft
    # das, worauf es ankommt.
    probe, rate = sprich("Test.", timeout=60)
    if not probe:
        print(f"FEHLER: {PIPER_HOST}:{PIPER_PORT} liefert kein Audio. "
              "Container und Modell pruefen (info.txt in Piper).")
        return 1
    print(f"Piper antwortet ({len(probe)} B Probe, {rate} Hz)")

    os.makedirs(TTS, exist_ok=True)
    if args.limit:
        posten = posten[:args.limit]

    fertig = neu = fehler = 0
    t0 = time.time()
    for i, it in enumerate(posten, 1):
        text = vorlese_text(it)
        name = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16] + ".mp3"
        ziel = os.path.join(TTS, name)
        vorhanden = os.path.exists(ziel) and os.path.getsize(ziel) > 500
        if vorhanden and not args.neu:
            it["tts"] = name       # auch aus einem frueheren, abgebrochenen Lauf
            fertig += 1
            continue
        pcm, r = sprich(text)
        if not pcm:
            fehler += 1
            print(f"  FEHLER bei {it['episode'][:40]}")
            continue
        it["tts"] = nach_mp3(pcm, r, ziel)
        neu += 1
        if neu % 10 == 0:
            schreibe(doc)          # Zwischenstand sichern, s. schreibe()
            print(f"  {i}/{len(posten)} ({time.time()-t0:.0f}s)", flush=True)

    schreibe(doc)

    groesse = sum(os.path.getsize(os.path.join(TTS, f)) for f in os.listdir(TTS)) / 1e6
    print(f"\nFERTIG: {neu} neu, {fertig} schon da, {fehler} Fehler")
    print(f"  web/tts/: {len(os.listdir(TTS))} Dateien, {groesse:.1f} MB")
    print("  library.json fortgeschrieben (Feld `tts`).")
    if fehler:
        print("  ⚠️ Fehler oben stehen lassen — die Seite nutzt dort die Browserstimme.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
