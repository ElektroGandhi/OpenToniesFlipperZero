# CLAUDE.md — OpenTonies

> Der **Katalog am Eingang**. Wird bei jedem Sitzungsstart geladen und bleibt
> deshalb kurz: Verbote, Wegweiser, Befehle, Fallen. Alles Ausführliche steht
> in den Dateien, auf die hier verwiesen wird — **erst lesen, wenn der Anlass
> es verlangt.**

## Was das ist

Flipper-Zero-App (C, `.fap`) plus eine Web-App. Das Kind sucht am Telefon eine
Hörspiel-Figur aus → Bluetooth → Flipper emuliert den NFC-Tag (SLIX-L,
ISO 15693) → die Toniebox spielt. Der Flipper liegt dabei **auf der Box**.

⚠️ **Eigenes Repo mit zwei Remotes:** `origin` = privates Hauptrepo, `github` =
öffentlich. Die öffentliche Historie ist getrennt: Neue Stände kommen als ein
Commit über `tools/github_spiegeln.sh` dorthin, nie per `git push github main`,
denn die private Historie enthält interne Dokumente (Zweig `intern-archiv`).

## ⛔ Die harten Verbote

1. **Kein Fremdmaterial committen.** Nie: `*.nfc`, `web/img/`, `web/library.json`,
   `tools/tonies_repo/`, `tonies.json`, `icons*/`, `tools/matches.json`. Das sind fremde
   Dumps und aus Produktfotos abgeleitete Bilder (siehe `NOTICE.md`). Committet
   werden **Werkzeuge, Code, Doku** — nie deren Ergebnis.
   Gegenprobe vor jedem Commit: `python3 tools/pruefe_repo.py`.
2. **Nichts behaupten, was nicht am Gerät lief.** Stand 07.11.2026 ist die
   Bluetooth-Kette **auf keiner Hardware getestet**. „Kompiliert" ≠ „funktioniert".
3. **Destruktives vorher vorlegen** (löschen, `rm`, Force-Push).
4. **Entscheidungen als Multiple-Choice vorlegen**, nicht als Fließtext.

## Wegweiser — welche Datei für welchen Anlass

| Der Auftrag klingt nach … | Dorthin |
|---|---|
| Flipper-App, Menü, Emulation, Setup, Bluetooth-Befehle | `src/toniekids.c` (eine Datei, ~1400 Zeilen) |
| Web-App, Kindermodus, Bibliothek, Farben, Layout | `web/index.html` (eine Datei, alles inline) |
| Wie die Web-App bedient wird + das BLE-Protokoll | `web/README.md` |
| **Oberfläche nachmessen nach jeder Layoutänderung** | `tools/pruefe_web.py` |
| Bibliotheksdaten, Bilder, Beschreibungen erzeugen | `tools/gen_library.py` |
| Neue Tonies aus der Gemeinschaftssammlung holen | `tools/update_tonies.py` |
| Spieldauern nachtragen | `tools/gen_durations.py` |
| Flipper-Icons (`.fxbm`) neu erzeugen | `tools/gen4.py` (die aktuelle Fassung) |
| Alte Arbeitsbücher, Befunde, Deploy-Notizen | privater Zweig `intern-archiv` |
| SD-Karte gegen die Sammlung abgleichen | `tools/sd_abgleich.py` |
| Gerät fernsteuern, Bildschirm fotografieren | `tools/flipper_rpc.py` |
| Demo-Bibliothek, eigene Figuren-Grafiken | `tools/demo_bibliothek.py`, `docs/media/quelle/` |
| Medien (Banner, Video, Musik) neu erzeugen | `docs/media/quelle/` |
| Zweiter Design-Entwurf (liegt parallel live) | `web/index2.html` |
| Beschreibungen vorlesen lassen (Piper) | `tools/gen_vorlesen.py`, Ergebnis in `web/tts/` |
| Was wann warum geändert wurde | `CHANGELOG.md` |
| Rechtliches | `NOTICE.md` |
| Vorstellung nach außen, Installation | `README.md` + `README.en.md`, immer beide |

## Befehle

```bash
# App bauen (ufbt liegt nicht im Standard-PATH)
cd src && PATH="$HOME/.var/app/com.vscodium.codium/data/python/bin:$PATH" ufbt

# Aufs Gerät + starten (nur mit Flipper an /dev/ttyACM0)
cd src && ufbt launch            # NICHT `loader open <Name>` — findet frische faps oft nicht

# Bibliothek + Bilder neu erzeugen (~40 s, lädt aus dem Netz)
python3 tools/gen_library.py

# Neue Tonies suchen / aufs Gerät
python3 tools/update_tonies.py --alle
python3 tools/gen_library.py
python3 tools/sd_abgleich.py               # Plan; schreiben mit --ausfuehren

# Web-App lokal starten (localhost gilt als sicher, Bluetooth geht)
cd web && python3 -m http.server 8000

# Oberfläche nachmessen — EIN Befehl, macht Server, Messung und Screenshots
python3 tools/pruefe_web.py                        # Entwurf 1
python3 tools/pruefe_web.py --seite index2.html    # Entwurf 2
# ⛔ BEIDE Entwürfe messen. Bis 12.09.2026 war "index.html" festverdrahtet;
#    index2.html wurde dadurch NIE geprueft, und das Werkzeug schwieg dazu.
#    Gefunden hat es erst ein Prüfer mit eigener Messung: sechs Kontrast-
#    Regressionen, darunter ein Lieblingsherz bei 1,02:1 (unsichtbar).
#    Die Pruefung selbst war die ganze Zeit da — sie las die falsche Datei.
# Beendet mit 0 = bestanden, 1 = durchgefallen. Danach die PNGs in /tmp ANSEHEN.
```

## Fallen, die hier schon zugeschnappt sind

**Web-App**
- **Der Screenshot findet, was die Zahlen nicht finden.** Überlauf, zerfressene
  Bilder, doppelte Titel — alle drei waren in jeder Messung grün. Nach jeder
  Layoutänderung das Bild **ansehen**, nicht nur Kennzahlen lesen.
- **Dafür die `_klein.jpg` nehmen, nicht die `.png`.** Ein 375×812-PNG ist ~100 kB;
  der Leseschutz-Hook dieses Baums schätzt daraus ~49.000 Token und blockiert.
  `pruefe_web.py` legt deshalb neben jedes PNG eine halbierte JPEG-Fassung
  (~10 kB) — die ist lesbar und reicht zum Beurteilen des Layouts.
- **Bewegung gehört hinter `prefers-reduced-motion`.** Der Block steht ganz oben
  im CSS und deckt auch Web-Animations-API-Aufrufe ab; JS-Animationen fragen
  zusätzlich selbst per `matchMedia` nach.
- **Das Regal darf sich nicht hinter dem Rücken des Kindes umsortieren.** Kinder
  merken sich Dinge über den Ort. `seriesOrder()` friert die Reihenfolge beim
  Laden ein; nur `setFav()` darf sie über `resetOrder()` neu bilden.
- **Ein Tipp OEFFNET, er spielt nicht mehr sofort.** Seit Beta 8/9 fuehrt jeder
  Tipp auf die Buehne — der gruene Knopf mit Dreieck startet, der rote mit
  Quadrat stoppt, ohne verbundenen Flipper sind beide ausgegraut. Der Stapel
  unterscheidet nach wie vor 163 Einzelfolgen von 97 Serien mit mehreren
  Folgen: ist ein Stapel sichtbar, oeffnet der Tipp die Folgenliste (statt
  direkt die Buehne). Zeile „52 Folgen" allein reicht nicht — das Kind
  liest nicht.
- **Deckkraft ist Teil des Kontrasts.** `opacity:.8` auf Text senkt ihn real.
  `pruefe_web.py` rechnet das mit ein — vorher fiel die Nebenzeile auf allen
  sechs Karten mit 3,84–4,19:1 durch, ohne dass es jemand merkte.
- **Die Kartenfarbe identifiziert nichts.** 271 Serien auf sechs Töne sind
  rund 45 Serien je Farbe. Sie ist Schmuck, kein Erkennungsmerkmal — keine
  Bedeutung hineinlegen.
- **Prüfseiten müssen vom selben Server kommen** wie die Zielseite, sonst ist
  `contentDocument` gesperrt und die Messung liefert **stumm nichts**.
- **Den Dunkelmodus nie von Hand nachbauen.** Eine handgepflegte Variablenliste
  vergisst genau die Variable, die man gerade geändert hat; der Test meldete so
  einen längst behobenen Fehler weiter. `_stage.html` liest den echten
  `prefers-color-scheme`-Block aus dem Stylesheet.
- **Deutsche Komposita brauchen `hyphens:auto` UND `overflow-wrap:break-word`.**
  Mit nur einem davon lief „Adventskalender" aus der Kachel.
- **Tippziele ≥ 76 px** im Kindermodus (Beleg: Kinder unter 9 verfehlen kleinere
  Ziele in bis zu 30 % der Versuche). 44/64 px sind Erwachsenenmaße.
- **Keine CDNs zur Laufzeit.** Die Schriften (Baloo 2 + Nunito, OFL) liegen
  LOKAL unter `web/font/` und werden mitgeliefert — Herkunft in
  `web/font/HERKUNFT.txt`. `ui-rounded` steht nur noch als Rückfall dahinter.
- **`filter` erzeugt einen Stapelkontext.** Das Bühnenbild trägt
  `drop-shadow` und wurde dadurch über den Zurück-Knopf gemalt: 52 % der
  Knopffläche waren tot. Solche Knöpfe brauchen ein eigenes `z-index`.
- **Die Bühne liegt über der Kopfleiste.** Ein Hinweis „oben rechts tippen"
  zeigt dort auf einen verdeckten Knopf. Was auf der Bühne gebraucht wird,
  muss auf der Bühne stehen.

**Bilder** (`gen_library.py`)
- Produktfotos in Shop-Auflösung sind zusammen **255 MB** — immer auf 400 px.
- **Freistellen nur bei deckendem hellem Rand.** Der Flood-Fill wächst sonst aus
  *durchsichtigen* Flächen heraus und frisst helle Figuren auf (Lars der Eisbär,
  Pummeleinhorn waren Fragmente). Cover behalten ihr Weiß.

**Bluetooth**
- GATT-Service ist **`8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000`**.
  `19ed82ae-…61fe0000` ist die **RX-Characteristic**, nicht der Service — beide
  enden auf `fe0000`, die Verwechslung liegt nahe.
- Web Bluetooth braucht **HTTPS oder localhost**; über `http://<IP>` verweigert
  der Browser wortlos. Auf dem iPhone gibt es kein Web Bluetooth.
- `bt_profile_start` startet den zweiten Kern neu → nie unter einem Mutex
  aufrufen. Empfang im BLE-Thread nur puffern, ausführen in der Hauptschleife.

**Sammlung**
- **Die Sammlung ändert sich rückwirkend.** Sie benannte `+` in `&` um und korrigierte
  `Lock EAS`. Der Abgleich vergleicht deshalb den Inhalt ohne dieses Feld und zeilenweise,
  weil auch die Zeilenenden abweichen.
- **Nicht-ASCII-Dateinamen scheitern an `storage.py send`.** Die Sammlung nutzt deshalb
  ae/oe/ue, und die Demo auch.

**Werkzeug**
- GitHub-Tarball statt Datei-für-Datei: ein Abruf statt Hunderter, und die
  Grenze von 60 API-Abrufen je Stunde wird nicht berührt.

## Wenn du etwas änderst

1. Bauen bzw. messen — und das Ergebnis **ansehen**.
2. `CHANGELOG.md` fortschreiben (neuester Eintrag oben).
3. Gegenprobe auf Fremdmaterial (siehe Verbot 1), dann committen.
4. Offenes ehrlich benennen. Was nicht am Gerät lief, heißt „ungeprüft".
