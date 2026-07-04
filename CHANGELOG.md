# Changelog

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
