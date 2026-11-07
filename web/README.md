# Handy-Bibliothek (Web-App) · Beta

> 🧪 **Beta:** An dieser Funktion arbeiten wir noch. Die Bluetooth-Verbindung ist auf echter
> Hardware noch nicht geprüft.

Die Folgen am Telefon aussuchen und per Bluetooth an den Flipper schicken, der sie für die
Toniebox emuliert.

**Zwei Ansichten in einer Seite:**

| | Kindermodus (Start) | Bibliothek |
|---|---|---|
| Für wen | das Kind | Erwachsene |
| Weg | Regal mit Figuren → Folge antippen → Bühne → grüner Knopf startet | Thema → Serie → Folge → Detail |
| Text | Beschriftung, nie Wegweiser | Beschreibung, Tracks, Volltextsuche |
| Zugang | ist die Vorgabe | **langes Drücken (0,8 s) auf die Überschrift** |

Der Kindermodus ist bewusst arm an Text: Ein Kind im Vorlesealter erkennt **Figuren**, keine
Kategorien wie „Hörspiel mit Liedern", und muss zum Abspielen nichts lesen können.
Ein Tipp auf das Bild **öffnet die Bühne** — dort liegt die Folge groß im Bild, ein
grüner Knopf mit Dreieck startet, ein roter mit Quadrat stoppt. Ohne verbundenen
Flipper sind beide ausgegraut und die Bühne selbst bietet den Verbindungsweg.
Das versteckte lange Drücken auf die Überschrift ist dasselbe Prinzip wie das Setup
in der Flipper-App.

**Lieblinge:** In der Bibliothek setzt ein Erwachsener bei jeder Serie ein Herz. Die
Lieblinge stehen im Kinderregal ganz oben — bei 260 Serien ist das der Unterschied
zwischen „findet es sofort" und „scrollt durch 130 Reihen". Zusätzlich merkt sich die
Seite, was oft gespielt wurde, und zieht es nach vorn. Versteckt wird nichts.

```
Telefon (diese Seite) --BLE--> Flipper (OpenTonies-App) --NFC--> Toniebox spielt
```

Der Flipper muss weiterhin **auf der Box liegen**. Das Telefon ersetzt nur das Blättern am
kleinen Flipper-Display, nicht das Hinlegen.

---

## Was hier liegt

| Datei | Herkunft | Im Repo? |
|---|---|---|
| `index.html` | eigener Code, keine externen Abhängigkeiten | **ja** |
| `library.json` | erzeugt von `tools/gen_library.py` | nein (§11) |
| `img/` | verkleinerte Tonie-Produktbilder, ~7 MB | nein (§11) |

`library.json` und `img/` sind **bewusst nicht committet** — es ist dieselbe Sorte
Fremdmaterial wie `tonies.json` (siehe `NOTICE.md`). Neu erzeugen:

```bash
python3 tools/gen_library.py            # ~40 s + Bilddownload
python3 tools/gen_library.py --no-images  # nur Metadaten
```

Das Werkzeug verbindet die eigene Sammlung (`tools/matches.json`) mit `tonies.json`
(Thema, offizielle Titel, Trackliste) und holt Inhaltstext und Spieldauer von den
tonies.com-Produktseiten. Es meldet am Ende ehrlich, wie weit es gekommen ist —
beim Stand vom 11.09.2026:

```
Folgen        : 612
Thema erkannt : 498  (81 %)
Beschreibung  : 345  (56 %)
Spieldauer    : 355  (58 %)
```

Die Lücken sind echt: 114 Folgen ließen sich keinem tonies.com-Eintrag zuordnen. Sie
erscheinen unter dem Thema **Sonstiges** und sagen in der Detailansicht offen, dass keine
Beschreibung vorliegt — statt eine zu erfinden.

---

## Betrieb

⚠️ **Web Bluetooth verlangt einen sicheren Kontext.** Die Seite läuft nur über **HTTPS**
oder über `http://localhost`. Von einer IP-Adresse im LAN per `http://` heraus verweigert
der Browser den Bluetooth-Zugriff wortlos — der Verbinden-Knopf tut dann einfach nichts.

Zum Ausprobieren am Rechner:

```bash
cd web && python3 -m http.server 8000
# -> http://localhost:8000  (localhost gilt als sicher, Bluetooth geht)
```

Für den Einsatz im Heimnetz braucht die Seite **HTTPS**, sonst verweigert der Browser
Bluetooth. Die Dateien lassen sich auf jedem statischen Webserver ablegen. Eine öffentliche
Demo mit erfundenen Figuren liegt auf
<https://elektrogandhi.github.io/OpenToniesFlipperZero/>.

Beim Ausrollen die Prüfseiten weglassen (`tar czf - --exclude='_*.html' .`).

Der Ausschluss `_*.html` haelt die Pruefseiten (`_measure.html`, `_stage.html`)
lokal — sie sind das Messgeraet, nicht die App. Das vorgeschaltete `rm -rf`
verhindert Zombie-Dateien aus einer aelteren Ausrollung.

### Browser

| Gerät | Geht? |
|---|---|
| Android, Chrome/Edge | **ja** |
| Desktop Chrome/Edge (Linux, Windows, macOS) | **ja** |
| iPhone/iPad, Safari | **nein** — Apple hat Web Bluetooth nie eingebaut |
| iPhone, Fremdbrowser mit eigener BLE-Brücke (z. B. Bluefy) | nur *in* der App; ein
  Homescreen-Symbol startet einen Web Clip ohne diese Brücke und damit ohne Bluetooth |

Für iOS führt kein Weg über Web Bluetooth. Wer das braucht, müsste den Bluetooth-Teil auf
einen Vermittler im Netz verlagern (Telefon spricht dann nur noch HTTP) — siehe Roadmap.

---

## Am Flipper

1. OpenTonies-App starten.
2. Verstecktes Setup öffnen: **langes Zurück** auf der Serien- oder Episoden-Ebene.
3. Eintrag **Bluetooth** auf **AN** (steht standardmäßig auf AUS, damit sich die App ohne
   Zutun genau wie vorher verhält). Die Einstellung hält über Neustarts.
4. Oben rechts im Display erscheint **`bt`** = Funk an und wartet, invers **`BT`** =
   das Telefon ist verbunden.

Dann in der Web-App oben auf **Verbinden** tippen und den Flipper aus der Liste wählen.

---

## Lieblinge — eine Liste, zwei Geräte

Langes Drücken auf eine Karte macht sie zum Liebling. Das ist **dieselbe Geste wie am
Flipper** (langes OK), damit Gerät und Telefon sich gleich bedienen lassen. Lieblinge
stehen im Regal ganz oben und tragen ein Herz.

Hängt der Flipper dran, führt **er** die Liste: Beim Verbinden holt die Web-App
`favorites.txt` vom Gerät und übernimmt sie; jede Änderung geht sofort zurück. Ohne
Flipper bleiben die Lieblinge lokal im Browser. Ein Gerät mit älterer App antwortet auf
`FAVS` nicht — dann bleibt die lokale Liste einfach stehen, statt geleert zu werden.

## Ohne Flipper benutzbar

Die ganze Oberfläche lässt sich ohne Gerät durchklicken: Antippen öffnet die Bühne
mit dem großen Bild und der Beschreibung. Ist kein Flipper verbunden, sind Abspielen
und Stopp ausgegraut, und auf der Bühne erscheint zusätzlich ein eigener Knopf
**„Mit dem Flipper verbinden"** — er übernimmt die Nutzergeste für den
Bluetooth-Dialog und spielt bei Erfolg direkt los. Verbunden wird sonst nur über
den Punkt oben rechts (kein automatischer Dialog beim Start).

## Neue Tonies nachladen

`tools/update_tonies.py` holt neue Dumps aus der Gemeinschaftssammlung
[nortakales/flipper-zero-tonies](https://github.com/nortakales/flipper-zero-tonies)
(Ordner `German/`, Struktur `<Serie>/<Folge>.nfc` — genau die Struktur, die der Flipper
erwartet).

```bash
python3 tools/update_tonies.py            # nur nachsehen, was neu wäre
python3 tools/update_tonies.py --push     # Neues auf den Flipper (USB)
python3 tools/gen_library.py              # danach Pflicht, sonst fehlen sie im Regal
```

Geladen wird der **Tarball** des Branches statt Datei für Datei: ein Abruf statt
Hunderter, und die GitHub-Grenze von 60 Abrufen je Stunde wird nicht berührt.
Stand 11.09.2026: 652 Dumps im Repo, 612 in der eigenen Sammlung — **40 neue** in
20 Serien (Pokémon, Marvel, Winnie Puuh, SuperKitties …).

Die Dumps landen unter `tools/tonies_repo/` und sind gitignored — Fremdmaterial nach §11,
genau wie Bilder und `library.json`.

## Das Protokoll

Klartext, zeilenweise mit `\n`. Bewusst lesbar statt binär — so lässt sich jeder Fehlerfall
mit einem beliebigen BLE-Terminal nachstellen.

| Gesendet | Antwort |
|---|---|
| `PING` | `PONG toniekids 2` |
| `LIST` | je Folge `I <Serie>/<Datei>.nfc`, am Ende `END <n>` |
| `PLAY <Serie>/<Datei>.nfc` | `OK PLAY <pfad>` oder `ERR <grund>` |
| `STOP` | `OK STOP` |
| `STATUS` | `ST play <pfad>` oder `ST idle` |
| `FAVS` | je Liebling `F <Serie>`, am Ende `ENDF <n>` |
| `FAV+ <Serie>` / `FAV- <Serie>` | `OK FAV+ <Serie>` / `OK FAV- <Serie>` |

Der Flipper nutzt dafür sein normales Serial-Profil, aber **ohne RPC** — die App übernimmt
den Kanal und bekommt die rohen Bytes.

GATT (verifiziert, leicht zu verwechseln):

```
Service : 8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000
TX      : 19ed82ae-ed21-4c9d-4145-228e62fe0000   Telefon schreibt -> Flipper
RX      : 19ed82ae-ed21-4c9d-4145-228e61fe0000   Flipper meldet   -> Telefon
```

`19ed82ae-…61fe0000` ist die **RX-Characteristic**, nicht der Service — die Verwechslung
liegt nahe, weil beide UUIDs auf `fe0000` enden.

---

## Bildaufbereitung

Rund 5 % der Produktfotos sind nicht freigestellt, sondern vor weissem Studiohintergrund
aufgenommen. Auf der Kachel steht dann ein weisser Kasten — im Dunkelmodus besonders
hässlich. `gen_library.py` entfernt ihn, aber **nur unter drei Bedingungen**, weil ein
Bild mit weissem Grund ein Schönheitsfehler ist und eine zerfressene Figur ein Datenschaden:

1. **Nur Bilder mit deckendem hellem Rand** werden überhaupt angefasst. Die 95 % bereits
   freigestellten bleiben unberührt. *(Ohne diese Prüfung wuchs der Flood-Fill aus den
   durchsichtigen Bereichen heraus und frass sich in helle Figuren — Lars der Eisbär und
   das Pummeleinhorn waren danach Fragmente.)*
2. **Nur vom Rand her.** Weiss mitten im Motiv (Augen, Schrift auf einem Cover) bleibt.
   Bleibt ein fast vollständiges Rechteck übrig, ist es ein **Cover** — dort gehört Weiss
   zum Bild, und es wird nichts entfernt (Asterix, WAS IST WAS, Paw Patrol).
3. **Zerfrans-Prüfung als zweites Netz:** Der Randanteil der Silhouette trennt heil von
   zerfressen (nachgemessen: zerfressen 0,065–0,116, heil 0,032–0,058). Über 0,060 wird
   das Freistellen verworfen.

Anschliessend wird jedes Bild auf sein Motiv zugeschnitten und mittig auf eine
quadratische 400er-Leinwand gesetzt — die gemeinsame Bounding-Box, ohne die die Figuren
unterschiedlich gross wirken und jede Regalreihe unruhig wird.

Ergebnis (11.09.2026): **0 von 562** Bildern mit weissem Hintergrund, vorher 27. Kein
beschädigtes Motiv — die 52 Bilder mit hohem Randanteil sind filigrane Figuren
(dünne Arme, Zauberstäbe, ein Ast), keine Schäden.

## Nachmessen statt ansehen

`_measure.html` und `_stage.html` sind Prüfseiten (nicht Teil der App, werden nicht mit
ausgerollt). Sie laden `index.html` in einem 375-px-Rahmen — **vom selben Server**, sonst
ist `contentDocument` gesperrt und die Messung liefert stumm nichts.

```bash
cd web && python3 -m http.server 8899 &
C=/var/cache/ms-playwright/chromium-1223/chrome-linux64/chrome
"$C" --headless=new --no-sandbox --virtual-time-budget=9000 \
     --dump-dom http://localhost:8899/_measure.html | grep -o '<title>[^<]*</title>'
"$C" --headless=new --no-sandbox --virtual-time-budget=10000 --window-size=375,812 \
     --screenshot=/tmp/s.png "http://localhost:8899/_stage.html?dark=1"
```

Zahlen aus dem Werkzeuglauf uebernehmen (`python3 tools/pruefe_web.py`) statt sie
hier von Hand zu pflegen — sie sind sonst nach jeder Layoutaenderung wieder falsch.
Bestanden bedeutet: Fensterbreite echte 375 px (nicht die 500-px-Klemme), kein
waagerechtes Scrollen, alle Tippziele im Kindermodus >= 76 px, alle Textfarben
gegen ihren Grund ueber der WCAG-Schwelle (Fliesstext 4,5:1, Grosstext 3:1).

⚠️ `_stage.html` liest den `prefers-color-scheme`-Block **aus dem Stylesheet der Zielseite**
statt ihn nachzubauen. Eine handgepflegte Variablenliste vergisst genau die Variable, die
man gerade geändert hat — hier meldete der Test dadurch einen bereits behobenen
Kontrastfehler weiter.

Drei Fehler wurden ausschließlich im angesehenen Screenshot gefunden, nicht in den
Zahlen: unterschiedlich große Figuren, ein aus der Kachel laufendes „Adventskalender",
und ein doppelt gezeigter Titel bei Einzelfolgen. Eine Geometrieprüfung beantwortet
„steht es sich im Weg?", nie „sieht es richtig aus?".

## Was noch offen ist

- **Nicht am Gerät getestet.** Stand 11.09.2026 kompiliert die App (`APPCHK`, API 87.1),
  war aber noch an keinem Flipper und an keiner Toniebox. Beim Schreiben hing kein Gerät
  an `/dev/ttyACM0`.
- **Ungeprüft: Bluetooth und NFC-Emulation gleichzeitig.** Beides liegt auf getrennten
  Bausteinen, aber ob die zeitkritische ISO-15693-Emulation den Funkbetrieb verträgt, ist
  nicht gemessen. Das ist das größte offene Risiko dieses Umbaus. Prüfen mit
  Setup → `Log` = AN und anschließend `log.txt` lesen.
- `LIST` blockiert die Flipper-Bedienung für einige Sekunden (liest jedes Serienverzeichnis).
  Die Web-App braucht es nicht zum Abspielen.
