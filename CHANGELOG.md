# Changelog

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
