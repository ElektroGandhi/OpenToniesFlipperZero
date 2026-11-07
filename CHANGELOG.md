# Changelog

## v1.0.0-beta.13 — Puffer, dritte Ordnerebene, Repo-Neuaufstellung (2026-11-07)

### Deutsch

**Neu in der App**
- **Puffer für den Auto-Timer:** Setup-Eintrag mit +0 bis +30 Minuten, voreingestellt +5. Er wird
  auf die echte Spieldauer und auf den eingestellten Timer-Wert aufgeschlagen. Am Gerät geprüft:
  1 min Dauer + 5 min Puffer endete nach 6 min.
- **Dritte Ordnerebene:** Die Gemeinschaftssammlung ordnet Figuren jetzt auch als
  `Book Tonies/Conni/Folge.nfc` ein. Solche Folgen waren vorher unerreichbar.
- Die App baut jetzt auch für die offizielle Firmware (API 88.2, nicht am Gerät geprüft).

**Werkzeuge**
- `tools/sd_abgleich.py`: vergleicht die SD-Karte direkt mit dem Stand der Sammlung und übernimmt
  Umbenennungen, ohne etwas zu löschen.
- `tools/demo_bibliothek.py`: fünf erfundene Figuren, damit sich die App ohne fremdes Material
  ausprobieren lässt.
- `tools/flipper_rpc.py`: Tasten und Bildschirmfotos per USB, ohne Zusatzpaket.
- `tools/pruefe_repo.py`: Fremdmaterial, interne Adressen, Gleichlauf der READMEs.
- `gen4.py` zeigte auf einen gelöschten temporären Pfad und erzeugte deshalb keine Bilder mehr;
  repariert. `gen_durations.py` schlägt nur noch fehlende Dauern nach.

**Repo**
- Die Bibliothek fürs Telefon über Bluetooth ist als Beta gekennzeichnet.
- Zweisprachig: `README.md` (Deutsch, Standard) und `README.en.md`, CI prüft den Gleichlauf.
- CI, Release-Workflow, Web-Demo mit erfundenen Figuren, eigene Grafiken, Video.
- GitHub erkennt die Lizenz jetzt als MIT; Hinweise stehen in `NOTICE.md`.
- Binärdatei, Bilder mit Figurenmotiv, interne Doku und Vorstufen-Skripte aus dem Baum entfernt.

### English

**New in the app**
- **Auto-timer buffer:** a setup entry from +0 to +30 minutes, +5 by default. It is added to the
  real running time and to the configured timer value. Checked on the device: 1 min duration +
  5 min buffer ended after 6 min.
- **Third folder level:** the community collection now also files figures as
  `Book Tonies/Conni/Episode.nfc`. Such episodes used to be unreachable.
- The app now also builds for the official firmware (API 88.2, not checked on a device).

**Tools**
- `tools/sd_abgleich.py`: compares the SD card directly with the collection and applies renames
  without deleting anything.
- `tools/demo_bibliothek.py`: five made-up figures, so the app can be tried without third-party
  material.
- `tools/flipper_rpc.py`: buttons and screenshots over USB, with no extra package.
- `tools/pruefe_repo.py`: third-party material, internal addresses, READMEs in step.
- `gen4.py` pointed to a deleted temporary path and no longer produced images; fixed.
  `gen_durations.py` now looks up only missing running times.

**Repository**
- The phone library over Bluetooth is marked as a beta.
- Bilingual: `README.md` (German, default) and `README.en.md`, with CI checking they stay in step.
- CI, release workflow, web demo with made-up figures, original graphics, video.
- GitHub now detects the license as MIT; notices are in `NOTICE.md`.
- Removed the binary, images showing figure motifs, internal docs and legacy scripts from the tree.

## v1.0.0-beta.12 — was fünf Prüfer fanden (2026-09-12)

### Das Messgerät las die falsche Datei
`tools/pruefe_web.py` hatte `index.html` an vier Stellen **festverdrahtet**.
Der zweite Entwurf wurde damit nie gemessen — und das Werkzeug schwieg dazu,
statt zu warnen. Jetzt `--seite index2.html`, und ein Tippfehler im Namen
bricht ab, statt "BESTANDEN" zu melden.

Dazu: `main()` wurde **ohne `sys.exit()`** aufgerufen. Der Rückgabewert ging
verloren, das Werkzeug endete immer mit 0 — auch bei "DURCHGEFALLEN". Der
eigene Docstring versprach das Gegenteil. In einer CI hätte die Prüfung
stillschweigend nie gegriffen. Beide Richtungen am Fehlerfall gemessen
(fehlende Datei → 1, Durchfaller → 1, Bestanden → 0).

### Sechs Kontrast-Regressionen im zweiten Entwurf
Alle aus derselben Ursache: beim Farbtausch auf die satte Palette wurde
**nicht nachgemessen**, und die alten Zahlen blieben als Begründung stehen.

- **Das Lieblingsherz war unsichtbar.** `#c62828` trug auf den sechs satten
  Tönen 1,02–1,56:1 (Soll 3:1) — auf allen sechs. Es ist das *einzige*
  Zeichen für "Liebling". Jetzt weiß mit dunkler Kontur.
- **Der Tastaturfokus war unsichtbar.** 1,05–1,34:1 gegen die Karten.
- **Nebenzeile, Bühnentext, Ersatzzeichen**: `opacity` .88/.75/.78/.55 ergaben
  3,26–4,43:1 — drei bis fünf von sechs Tönen durchgefallen. Deckkraft
  entfernt; Grad und Schnitt tragen die Hierarchie. Das ist robuster:
  Deckkraft rechnet gegen einen Grund, den man beim Farbtausch vergisst.
- **`.favbtn.on` unterschied sich nur durch Farbe** (WCAG 1.4.1), bei 2,16:1.
  Jetzt trägt die Fläche den Zustand.
- **Das Regalbrett fehlte im Dunkelmodus** — `--brett` wurde dort nie gesetzt,
  das helle Braun trug 1,11–1,54:1 gegen die Dunkelkarten. Die braune
  t6-Karte verschmolz mit ihrem eigenen Brett.

### Das Herz fehlte an der halben App — in beiden Entwürfen
`heart.style.display = opts.fav` las ein Feld, das nur an **einem** der zwei
`cardFor()`-Aufrufe übergeben wird. In der Folgenliste war es `undefined`, das
Herz also immer versteckt — während der Screenreader korrekt "Liebling" sagte
(zwei Zeilen darüber wird derselbe Wert richtig berechnet). Zwei Namen für
dieselbe Sache, einer optional.

Die Wipp-Animation für Lieblinge war ebenfalls **tot**: die Klasse `hatherz`
kam in der ganzen Datei genau einmal vor, nämlich in der Regel selbst. Und
hätte sie gegriffen, hätte sie die Figur um 30 px hochgerissen — `translateY`
addiert sich auf das bestehende `margin-top:-30px`.

### Piper: meine eigene Falschaussage zurückgenommen
In `gen_vorlesen.py`, `FORTSETZUNG.md` und Gitea #1016 stand, `describe`
antworte mit einem leeren Objekt. **Das ist falsch** — gemessen: 7 Schlüssel,
piper 2.4.3, 164 Stimmen, `frank_v8` dabei. Leer sieht es nur, wer
`data_length` ignoriert, also *derselbe* Leserfehler, den diese Dateien als
Ursache benennen. Die Fehldiagnose war eine Kette aus einer Ursache, und jede
Stufe bestätigte die vorige. **Eine zweite Messung mit demselben kaputten
Werkzeug ist keine zweite Messung.**

Ebenfalls richtiggestellt: der `voices.json`-Mount war **nie committet**
(`git log -S` leer, `git diff --numstat` = 11/0). Er entstand im selben
Arbeitsgang, der ihn gemeldet hat — kein Altlast-Fund, sondern ein eigener
Reparaturversuch an einem Defekt, den es nicht gab.

### Vorlesen: 86 verwaiste MP3s wieder verknüpft
`library.json` kannte 190 Dateien, auf der Platte lagen 253. Ursache: ein noch
laufender Lauf mit älterem Code schreibt den Index erst am Ende. Neu:
`--nur-index` verknüpft vorhandene Dateien rein rechnerisch nach (190 → 276),
ohne Piper zu rufen.

Dazu ein **Lost-Update-Schutz**: `schreibe()` hob bisher den Stand aus dem
Speicher zurück und hätte damit jede Änderung von `gen_library.py` aus den
letzten ~90 Minuten Laufzeit verworfen. Jetzt wird nur das Feld `tts` in den
frischen Stand von der Platte gehoben — über `path`, weil das das einzige
Feld ist, das gefüllt **und** eindeutig ist (652/652). Ein `id`-Feld gibt es
nicht; ein Merge darüber hätte jedem Eintrag das `tts` des letzten verpasst.

### Sieben stehengebliebene Messzahlen berichtigt
`--heart` "4,18:1", `.cnt` "6,04–7,73:1", `--line` "1,25:1", `--bg2`/`--ink2`
"4,28:1" (echt: 10,17:1) und ein Querverweis auf eine Zeile, die es nicht mehr
gibt. Alle waren Entwurf-1-Werte, die als Begründung für Entwurf-2-Code
dastanden — die gefährlichste Sorte Doku-Drift, weil sie das Nachmessen
*verhindert*.

### Zurückgenommen: "die Figur ragt 30 px über die Karte"
Gemessen ragt sie **1 px** heraus (Kastengeometrie: 30 − 26 Polster − 3 Rand),
und das erste gemalte Motivpixel liegt 34–40 px **innerhalb** der Karte. Grund:
die 400×400-webp haben transparente Ränder von 4–33 % der Höhe (25 Stichproben,
Median 23,5 %). Ein einheitliches `margin-top` kann das nicht ausgleichen —
dafür müsste `gen_library.py` beim Freistellen auf die Motivgrenze zuschneiden.
**Offen, nicht behoben.**

## v1.0.0-beta.11 — Ton, Kopfbild, zweiter Entwurf (2026-09-12)

### Vorlesen: es war nichts zu hoeren, und das hatte zwei Gruende
- **73 % Chance auf Stille.** Von 652 Folgen haben nur 354 eine Beschreibung.
  Bei den anderen 298 war der Lautsprecher-Knopf **ausgeblendet**, ohne
  Erklaerung. Jetzt wird ohne Beschreibung der NAME vorgelesen
  ("Janosch. Oh wie schoen ist Panama.") — fuer ein Kind, das nicht liest,
  ohnehin das Wichtigere. Damit hat jede Folge Ton.
- **Der Index wurde erst am Ende geschrieben.** 154 MP3 lagen fertig auf der
  Platte, `library.json` kannte 3 davon. `gen_vorlesen.py` schreibt jetzt alle
  10 Dateien atomar und verknuepft beim Start auch, was ein abgebrochener Lauf
  schon erzeugt hat. 190 Folgen sprechen mit Piper-Stimme, live bestaetigt.
- **`speechSynthesis.getVoices()` ist asynchron** und liefert beim ersten
  Aufruf ein LEERES Array (nachgemessen: 0 Stimmen). Der Rueckfall haette
  deutschen Text englisch ausgesprochen. Wartet jetzt auf `voiceschanged`.

### Kopfzeile: Bild statt Schriftzug
Oben links steht eine **Figur** — im Regal die oberste, in einer Serie deren
eigene. Der Schriftzug bleibt fuer Erwachsene und Screenreader, tritt aber
zurueck. In der Bibliothek ist das Bild aus.
⚠️ Beim Einbau passte der Anker nicht mehr (der Titel ist inzwischen ein `<h1>`
mit `tabindex`) — die Folge war ein toter Bildschirm mit "Cannot set properties
of null". `kopfbild()` bricht jetzt ab, wenn das Element fehlt. Gefunden nur im
angesehenen Screenshot; die Kennzahlen sagten "BESTANDEN".

### Zweiter Entwurf (`index2.html`)
Nach viermal "langweilig": Nachthimmel statt Papier, satte statt blasser
Farben, Regalbrett unter jeder Karte, Figuren die herausragen, Lieblinge die
wippen. Beide Fassungen liegen live zum Vergleich. Einzelheiten und die zwei
CSS-Fallen stehen in `FORTSETZUNG.md`.

### ai_piper (Gitea #1016, geschlossen)
Der `voices.json`-Mount aus einem Reparaturversuch ist zurueckgebaut. Er war
**wirkungslos** — Piper hat immer funktioniert, der Fehler lag in einem Client,
der das `data_length`-Feld des Wyoming-Rahmens ignorierte. Abnahme nach dem
Rueckbau: 33 audio-chunks, 66560 B PCM. Im Compose steht jetzt eine Warnung an
der Stelle, samt dem Befund, dass der Healthcheck nur den offenen Port prueft.

## v1.0.0-beta.10 — Nachlese aus den Rohbefunden (2026-09-12)

Zweiter Durchgang durch `BEFUNDE-verifikation.md`. Die harten Sachen waren mit
beta.9 raus, die restlichen kleineren Punkte sind hier — alle statisch belegt,
kein Hardware-Test moeglich.

### Web-App
- **`waiters` von vorn durchlaufen.** Antworten kamen in Reihenfolge der
  Anfragen, aber der Verteiler suchte von hinten — das generische `ERR ...`
  fing der spaetere Warter ab, der eigentlich gemeinte lief in den Zeitablauf.
- **`prefers-reduced-motion` bremst jetzt auch `animation-delay`.** Ohne den
  Zusatz blieben gestaffelt eingezogene Karten bis 120 ms unsichtbar, weil
  `.card.rein` seinen Start-Zustand `backwards` haelt.
- **`.shelfsep`, `.libhint`, `.empty`** benutzen `--ink` statt `--ink2`:
  auf der unteren Verlaufsfarbe der Seite (`--bg2`) fiel `--ink2` auf 4,28:1
  und damit unter die 4,5:1-Fliesstext-Schwelle.
- **`.row .t` und `.detail h1`** brechen deutsche Komposita jetzt sauber
  (`hyphens:auto` + `overflow-wrap:break-word`) — Ueberhaenge waren nicht in
  der Kachel-Ansicht, aber in Trefferliste und Detail sichtbar geworden.
- **Doppelter, widerspruechlicher Kommentarblock** vor `play()` weg
  (behauptete "spielt sofort" gegen die neue Realitaet "OEFFNET").
- **`btAsked`** entfernt (deklariert und einmal gesetzt, nirgends gelesen —
  Rest eines nicht mehr existierenden Auto-Verbindungsdialogs).
- **`LIB.themes`** entfernt (nie gelesen, `BY_THEME` wird in `build()` aus
  `it.theme` gebildet). `LIB = {items:[]}`.
- **`.note`-CSS-Klasse** weg (nirgends erzeugt).

### Doku
- **`web/README.md` Deploy-Befehl** an CLAUDE.md angeglichen — mit
  `rm -rf` und `--exclude='_*.html'` (die Pruefseiten gehoerten nicht mit
  ausgerollt und Zombie-Dateien blieben liegen).
- **`web/README.md` "Ohne Flipper benutzbar"** auf den Ist-Zustand
  umgeschrieben (Buehne + eigener Verbindungsknopf, kein automatischer Dialog).
- **Kachel/Kontrast-Kennzahlen** aus `web/README.md` gestrichen — sie waren
  seit beta.8 falsch (162×236, drei Schriftgroessen). Der Text verweist
  jetzt auf `pruefe_web.py`, damit sie nicht wieder driften.
- **CHANGELOG**: die falsche "125 Zeilen"-Angabe zu `CLAUDE.md` in beta.9
  entfernt (Datei hat 155 Zeilen; die Zahl gehoert nicht ins Changelog,
  sie veraltet mit jedem Commit).

### Offen (aufgeschrieben, nicht ausgefuehrt — Freigabe noetig)
- **`ble_profile_serial_notify_buffer_is_empty`** in `src/toniekids.c`
  einbauen — nach 192 empfangenen Byte meldet der Flipper laut Befund
  dauerhaft "0 Byte frei". Braucht einen `ufbt`-Buildtest am Gerät (falsche
  Signatur = kein `.fap`).
- **`home_devpreview/nginx.conf`** (Elternrepo): `gzip` fuer `library.json`
  (spart ~75 % Ladegewicht), `application/manifest+json` fuer `.webmanifest`,
  `autoindex off` fuer `/opentonies/img/`. Eingriff am laufenden Reverse-Proxy.
- **Historien-Purge der `montage_*`/`preview_*`-PNG mit Figurenmotiv** aus
  dem oeffentlichen GitHub-Remote. Destruktiv, deshalb nicht ausgefuehrt.
- **Font-Deduplikation** (`Baloo2-500.woff2` und `Nunito-800.woff2` sind
  byteweise Duplikate der 800er bzw. 400er Datei — variable Schriften).
  Loeschen ist destruktiv, deshalb nicht ausgefuehrt.

## v1.0.0-beta.9 — Verifikation aufgeraeumt (2026-09-12)

Grundlage: 87 Rohbefunde aus einer Zehn-Pruefer-Verifikation, jeder einzeln
gegengeprueft. Rund die Haelfte hat die Gegenpruefung ueberlebt. Die
folgenden Aenderungen sind alle statisch belegt — **weiterhin nicht am
Geraet getestet**.

### Neu (Ablauf)
- **Ein Tipp OEFFNET die Buehne, er spielt nicht mehr sofort.** Der gruene
  Knopf mit Dreieck startet, der rote mit Quadrat stoppt. Ohne verbundenen
  Flipper sind beide ausgegraut und die Buehne selbst bietet den
  Verbindungsweg — der Hinweis "oben rechts tippen" zeigte vorher auf einen
  Knopf, den die Buehne verdeckte.
- **Escape schliesst die Buehne** (Tastatur), die Buehne meldet sich als
  `role="dialog"` mit `aria-modal`.

### Behoben (Web-App)
- **Buehne war eine Sackgasse** (52 % des Zurueck-Knopfs tot; Verbindungspunkt
  verdeckt). `#stageback` bekommt `z-index:2`, die Buehne hat einen eigenen
  Verbindungsknopf.
- **Suche fuehrte in eine Sackgasse**: der Klick auf einen Treffer oeffnete
  die Detailansicht — aber `query` blieb gesetzt, der Suchzweig griff wieder
  und die Detailansicht war unerreichbar.
- **`playing` und `rxBuf` ueberlebten das Trennen**: nach dem Wiederverbinden
  zeigte die Buehne einen aktiven Stopp-Knopf fuer eine tote Folge, und der
  erste PING klebte am Rest der letzten Zeile.
- **Kontraste**: `#stage .sr/.st` von 2,59:1 auf >= 5:1 (color:var(--ink2)
  hatte unbemerkt --tink ueberschrieben); `#stage .desc .leer` von .7 auf
  .78 Deckkraft; Stapel-Streifen mit sichtbarer Kante (vorher 1,23:1).
- **Barrierefreiheit**: Suchfeld hat `aria-label`, `#link` traegt
  `aria-pressed` und wechselnden Namen (verbunden/trennen), Serien-Karten
  fuehren den Lieblings-Zustand im `aria-label` statt in einem
  bedeutungslosen `aria-pressed`, Bibliothek-Herz-Knopf hat `aria-pressed`.
  `#msg` und `#stagest` sind Live-Regionen (`role="status"`).

### Behoben (Flipper-App)
- **`load_favorites` las nur 2047 Byte** — ab 117 Lieblingen ging der Rest
  beim naechsten Speichern verloren. Liest jetzt die volle Datei.
- **`ble_rx_len` und die verworfene Fehlerzeile bei PLAY** — nach einem
  fehlgeschlagenen PLAY zeigte der Flipper weiter "SPIELT!"; nach einem
  Verbindungsabbruch klebte der halb empfangene Befehl am naechsten.
- **PLAY-Fehlerzweig setzt Bildschirm zurueck**, nach `emulate_stop` bleibt
  `screen` sonst auf `ScreenPlay`, obwohl gar nichts laeuft.

### Behoben (Werkzeug)
- **`update_tonies.py` -> `gen_library.py` Kette fuehrte ins Leere.**
  `gen_library.py` iterierte nur ueber `matches.json`, das niemand
  fortschrieb. Liest jetzt auch `tools/tonies_repo/`. Bild-URL kommt aus dem
  `pic`-Feld von tonies.json. **Bibliothek 612 → 652 Folgen**, live
  bestaetigt.
- **`gen_library.py`**: `library.json` wird atomar geschrieben (.tmp +
  os.replace). Bricht bei fehlenden Ausgaben ab statt still weniger zu
  liefern. `--help`/`--limit` per `argparse`. `tonies.json`-Cache wird auf
  gueltiges JSON geprueft, kaputter Cache wird neu geholt.
- **Spieldauer** aus dem `runTime`-JSON-Feld der Produktseite statt aus
  einer nie treffenden Freitextsuche.

### Doku
- **Gegenprobe in CLAUDE.md Verbot 1** deckt jetzt alle sechs verbotenen
  Pfade ab (vorher fehlten `tonies.json` und `icons*/`).
- **Fallen ergaenzt**: `filter` erzeugt einen Stapelkontext (Buehnenbild
  ueber Zurueck-Knopf); die Buehne liegt ueber der Kopfleiste. "Keine
  Webfonts" richtiggestellt — Baloo 2 + Nunito liegen lokal unter
  `web/font/`.

## v1.0.0-beta.8 — Lebendigkeit, belegt statt geraten (2026-09-11)

Grundlage: eine Recherche ueber sechs Blickwinkel (echte Kinder-Apps, Forschung
zu 5- bis 8-Jaehrigen, Bewegung, Farbe, Freude, Anti-Muster), verdichtet und
anschliessend adversarisch gegengeprueft. Die Gegenpruefung hat drei Vorschlaege
verworfen und zwei Rechenfehler in der eigenen Empfehlung gefunden.

### Der wichtigste Fund war kein Schmuck, sondern ein Bedienfehler
**163 der 260 Serien haben genau eine Folge** — ein Tipp spielt sofort los. Die
uebrigen 97 oeffnen ein Untermenue. Der einzige Hinweis darauf war die Textzeile
"52 Folgen" in der kleinsten Schrift. Fuer ein Kind, das nicht liest, ist der
Unterschied damit unsichtbar gewesen. Jetzt zeigt ein sichtbarer **Kartenstapel**
ohne ein Wort, dass mehr als eins drin liegt.

### Neu
- **Die Figur steht auf der Karte**, statt daraufgedruckt zu sein: Schlagschatten
  am Motiv plus Kontaktellipse, die beim Druck mitschrumpft.
- **Heldkarte**: die meistgehoerte bzw. erste Lieblingsserie ueber die volle
  Breite. Ein gleichfoermiges Raster aus 260 Kacheln hat keinen Blickanker.
  Erscheint NUR mit echtem Grund — sonst waere es die alphabetisch erste Serie,
  und willkuerliche Hervorhebung faellt Kindern auf.
- **"Ueberrasch mich"** startet eine zufaellige Folge. Neugier war in der
  Forschung der staerkste Einzelfaktor fuer Freude — staerker als Belohnungen.
  Bewusst OHNE Punktestand, Serien oder Abzeichen (ICO Children's Code).
- **Startbildschirm-Auftritt**: Manifest, eigenes Icon, `standalone`,
  `theme-color`. "Meine App ohne Adressleiste" ist fuer ein Kind mehr als jede
  Animation. Das Icon ist selbst gezeichnet, kein Produktfoto (§11).
- **Langes Druecken zeigt seine 600 ms**: das Herz waechst waehrend des Haltens
  auf und schnappt ein. Vorher lag der Finger 600 ms auf einer reglosen Karte.
- **Gestaffelter Einzug** beim Ebenenwechsel, 20 ms Versatz, **hart gedeckelt
  bei 7 Karten** — ueber alle 260 gelegt waere die letzte erst nach 5,2 s da.

### Behoben
- **`prefers-reduced-motion` fehlte komplett** (0 Treffer in der Datei). Jede
  Bewegung war damit ein Barrierefreiheitsfehler.
- **Das Regal sortierte sich hinter dem Ruecken des Kindes um**: nach dem
  Abspielen zaehlte `bump()` hoch, und beim Zurueckgehen stand alles anders.
  Kinder merken sich Dinge ueber den ORT. Die Reihenfolge friert jetzt beim
  Laden ein; nur das Setzen eines Lieblings ordnet neu.
- **Nebenzeile auf den Karten fiel durch**: 3,84–4,19:1 statt 4,5:1, auf allen
  sechs Farben. `pruefe_web.py` rechnet jetzt Deckkraft mit ein und findet es.
- **Stopp-Knopf hell nur 3,81:1** — beim Umbau auf die froehliche Palette
  geaendert und nicht nachgemessen. Jetzt 5,02:1.
- Herz ohne `aria-label`/`aria-pressed`; Karten ohne sprechenden Namen.
- Quelltextkommentar behauptete, die Kartenfarbe sei ein Wiedererkennungsanker.
  Das ist bei 37–52 Serien je Farbe schlicht falsch und steht jetzt richtig da.

### Bewusst NICHT gemacht
Dauerbewegung im Regal (zieht den Blick vom Inhalt), Konfetti auf jeden Tipp
(Belohnung der blossen Handlung senkt messbar die Ausdauer), Streaks/Punkte/
Abzeichen (ICO Children's Code), Klanguntermalung als Dauerloesung (die Toniebox
liefert den Ton — ein zweiter Kanal konkurriert mit dem Hoerspiel).

### Werkzeug
- **`tools/pruefe_web.py`**: ein Befehl misst Ueberlauf, Tippziele,
  Schriftgroessen und alle Kontraste hell wie dunkel und legt Screenshots ab —
  daneben je eine kleine JPEG-Fassung, weil der Leseschutz dieses Baums ein
  100-kB-PNG als ~49.000 Token einschaetzt und blockiert.
- **`CLAUDE.md`**: Katalog am Eingang mit Verboten, Wegweiser, Befehlen und
  den Fallen, die hier schon zugeschnappt sind — damit auch ein kleines
  Modell ohne 6.000 Woerter Doku arbeiten kann.

## v1.0.0-beta.7 — Handy-Bibliothek über Bluetooth (2026-09-11)

⚠️ **Noch nicht am Gerät getestet.** Die App kompiliert sauber (`APPCHK`, Target 7,
API 87.1), war aber an keinem Flipper und an keiner Toniebox — beim Bauen hing keines an
`/dev/ttyACM0`. Alles unten ist am Quelltext und am SDK belegt, nicht am laufenden System.

### Neu
- **Fernsteuerung per Bluetooth.** Die App übernimmt das Serial-Profil des Flippers
  (`bt_profile_start` + `ble_profile_serial`, **ohne RPC**) und nimmt Klartextbefehle
  entgegen: `PING` · `LIST` · `PLAY <Serie>/<Datei>.nfc` · `STOP` · `STATUS`.
  Zeilenweise und lesbar statt binär — jeder Fehlerfall lässt sich mit einem beliebigen
  BLE-Terminal nachstellen.
- **Web-App `web/index.html`** — die Bibliothek am Telefon: nach **Thema → Serie → Folge**
  gegliedert, mit Bild, Spieldauer und **Beschreibung je Folge**, dazu Volltextsuche über
  Titel, Beschreibung und Tracklisten. Eine Datei, keine externen Abhängigkeiten.
- **Werkzeug `tools/gen_library.py`** baut die Bibliotheksdaten: verbindet `matches.json`
  mit `tonies.json` (Thema, offizielle Titel, Tracks) und holt Inhaltstext und Spieldauer
  von tonies.com. Zuordnung in drei Stufen (Modellnummer → exakt → fuzzy), dazu ein
  Bildspiegel, der die Produktfotos von ~255 MB auf ~7 MB verkleinert.
  Abdeckung: 612 Folgen, **81 %** Thema, **56 %** Beschreibung, **58 %** Spieldauer.
  Die restlichen 114 Folgen stehen unter *Sonstiges* und sagen offen, dass keine
  Beschreibung vorliegt — statt eine zu erfinden.
- **Setup-Eintrag „Bluetooth"** (10. Eintrag). Standard **AUS**: ohne Zutun verhält sich die
  App exakt wie bisher. Der Wert zeigt nicht nur die Einstellung, sondern den echten
  Funkzustand (`AUS` / `startet` / `wartet` / `VERBUNDEN`).
- **Statusanzeige im Display** oben rechts: `bt` = an und wartet, invers `BT` = Telefon
  verbunden. Deckend gezeichnet wie der Favoriten-Stern, damit es über der Laufschrift
  lesbar bleibt.

### Sorgfalt im Detail
- **Eigener Schlüsselspeicher** (`ble_keys.bin`): Das Pairing mit dem Telefon überschreibt
  nicht die gespeicherten Schlüssel der offiziellen Flipper-App. Beim Beenden wird das
  Standardprofil wiederhergestellt.
- **Empfang und Ausführung getrennt.** Der BLE-Callback sammelt nur Bytes bis zum
  Zeilenende und weckt die Hauptschleife (gleiches Muster wie der Auto-Timer); ausgeführt
  wird ausschließlich dort. Ein eigener, kleiner Mutex nur für die Befehlsübergabe — nie
  gemeinsam mit dem Zeichen-Mutex gehalten, weil verschachtelte Sperren lautlos hängen.
- **Funkzustand als Soll-Ist-Abgleich** in der Hauptschleife statt im Tastendruck:
  `bt_profile_start` startet den zweiten Kern neu und darf keinen Mutex halten.
- **Flusskontrolle beim Senden**: schlägt `tx` fehl, ist der Puffer voll — dann warten statt
  Daten zu verlieren; nach 25 Versuchen wird abgebrochen und protokolliert.

### Offen
- **Ungeprüft: Bluetooth und NFC-Emulation gleichzeitig.** Getrennte Bausteine, aber ob die
  zeitkritische ISO-15693-Emulation den Funkbetrieb verträgt, ist nicht gemessen. Das ist
  das größte Risiko dieses Umbaus.
- **iPhone geht nicht.** Safari kann kein Web Bluetooth; ein Homescreen-Symbol startet auch
  aus einem Fremdbrowser heraus einen Web Clip ohne dessen BLE-Brücke. Android und Desktop
  funktionieren. Ausweg wäre ein Vermittler im Netz — siehe Roadmap.
- `LIST` blockiert die Flipper-Bedienung für einige Sekunden (liest jedes Serienverzeichnis).

## v1.0.0-beta.6 — Log & Timer-Präzision (2026-07-05)

### Neu
- **Log-Option im Setup** (`log.txt` mit ms-Zeitstempeln): protokolliert die Emulations-/
  Timer-Kette — u. a. „auto-timer AUS" vs. „timer scharf: Xmin" und das Feuern (auto-aus /
  replay). Damit lässt sich nachvollziehen, warum das Auto-Aus (nicht) auslöst.

### Fixes
- Timer nutzen jetzt `furi_ms_to_ticks` (korrekte ms→Ticks-Umrechnung, unabhängig von der
  Tick-Rate). **Auto-Aus verifiziert**: feuert punktgenau (~1 ms) nach der eingestellten Dauer.

## v1.0.0-beta.5 — Robustheit (2026-07-04)

### Fixes (nach interner Code-Review)
- **Kein Absturz bei leerer Sammlung**: OK auf dem „KEINE TONIES"-Screen (frische Installation
  ohne Figuren-Dumps) griff auf eine leere Liste zu → jetzt sauber abgefangen.
- **Kein Absturz bei korrupter `settings.txt`**: negative/ungültige Werte werden auf gültige
  Indizes geklemmt (vorher Out-of-bounds-Zugriff beim Start).
- Kleinere Härtungen: `strdup`-OOM-Prüfung in der Listen-Verwaltung; Marquee-Timer-Zugriff als
  bewusst-harmlos dokumentiert.
- Tool `gen_durations.py`: toten Kompilations-Fallback repariert + Präfix-Match mit Mindestlänge
  (verbessert die Trefferquote bei der nächsten Regenerierung).

## v1.0.0-beta.4 — (2026-07-04)

### Verbesserungen
- **Favoriten markieren unterbricht das Durchblättern nicht mehr**: der Cursor bleibt an
  Ort und Stelle (nur der Stern erscheint), statt der Serie an ihren neuen Platz nach vorne
  zu folgen. Favoriten wandern erst beim nächsten App-Start nach vorne — so kann man die
  ganze Bibliothek in Ruhe durchgehen und markieren.
- **Laufschrift langsamer + neue Stufe „sehr langsam"** (Sub-Pixel-Tempo):
  Aus / sehr langsam / langsam / mittel / schnell.

## v1.0.0-beta.3 — Hotfix (2026-07-04)

### Fixes
- **Favoriten-Stern** sitzt jetzt als Badge **im Bild** (oben links) statt über dem Namen —
  der Name bleibt dadurch voll lesbar (Laufschrift & Zeilen nicht mehr verdeckt).

## v1.0.0-beta.2 — Hotfix (2026-07-04)

### Fixes
- **Favoriten-Stern** wurde bei aktiver Laufschrift nicht mehr angezeigt — der Stern wird
  jetzt **immer** gezeigt (deckend gezeichnet, auch über dem Lauftext).

## v1.0.0-beta.1 — erste Beta (2026-07-04)

Erste öffentliche **Beta** von **OpenTonies** für den Flipper Zero. Das ist genau die
Version, die aktuell läuft und getestet wird.

### Features
- Kinderfreundliche Auswahl im **Hochformat** (Serie → Geschichte), komplett bildgeführt.
- **Direkte SLIX-L-Emulation** für die Toniebox (an echter Box bestätigt).
- **Favoriten** (langes OK) — Lieblingsserien zuerst.
- **LED-Rückmeldung** während der Emulation: an/aus, Farbe (7), Helligkeit (3).
- **Auto-Timer** mit **echten Spieldauern** (von tonies.com), sonst Fallback-Minuten;
  Aktion nach Ablauf: **Aus** (Strom sparen) oder **Replay**-Bounce (experimentell).
- Ebene 2 zeigt nur den **Episodentitel** (Serien-Präfix entfernt).
- **Verstecktes Setup** (langes Zurück): Schrift GROSS/klein, **Lese-Modus** ohne Bilder,
  LED, Auto-Timer, **Laufschrift** mit einstellbarem Tempo (Aus/langsam/mittel/schnell).
- **Spieldauer-Bibliothek** (`durations.txt`, ~58 %) — per Pull Request erweiterbar.

### Bekannt / offen
- **Auto-Replay** und das Timer-Auslösen an der echten Box noch abschließend zu bestätigen.
- Spieldauer-Abdeckung ~58 % (Rest steht meist nicht mehr auf tonies.com) — wächst über
  Community-PRs.

### Ausblick (nur Idee, noch nicht in Arbeit)
- **Web-App als Companion** auf jedem Endgerät (visuelle Auswahl, Start/Stop). Vorher
  machen wir unsere **Security-Hausaufgaben**.

---

> Beta-Hinweis: Enthält nur eigenen Code + Werkzeuge + Doku — **keine** Tonie-Dumps oder
> -Bilder (siehe README, Abschnitt „Rechtliches / Disclaimer").
