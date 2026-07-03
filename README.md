# OpenTonies – Flipper-Zero-App (HOCHFORMAT)
(Menü-/Anzeigename: **OpenTonies**, Icon: Tonies-„T"; interne appid/Dateien
weiterhin `toniekids`.)

Kinderfreundliches, grafisches Menü für die Toniebox-Figuren. Der Flipper wird
**senkrecht/hochkant** gehalten (64×128); oben ein **großes Bild (64×96)** der
Figur, darunter der Name. Zwei Ebenen: **Serie → Geschichte**. **OK auf einer
Geschichte emuliert die SLIX-L-Figur direkt** für die Toniebox.

Exakte Bildschirm-Vorschau: `preview_hochformat.png`

## Auf dem Flipper
- App: `SD:/apps/NFC/toniekids.fap` → Menü **Apps → NFC → „OpenTonies"**
- Bilder (64×96): `SD:/apps_data/toniekids/icons_p/<Serie>/<Geschichte>.fxbm`
  (je Serie zusätzlich `_series.fxbm`)
- Figuren: liest direkt `SD:/nfc/Toniebox Figuren/<Serie>/<Geschichte>.nfc`
- (Alte Querformat-Bilder unter `icons/` und `icons_s/` werden nicht mehr
  gebraucht und können gelöscht werden.)

## Bedienung (Flipper senkrecht halten)
- **← → / ↑ ↓**  vorige / nächste Serie bzw. Geschichte (alle Richtungen
  navigieren; **Taste halten = schnell blättern**)
- **OK**  Serie öffnen · Geschichte **abspielen** → Flipper auf die Box legen.
  Während der Emulation **blinkt die LED zyan** (wie beim eingebauten NFC-Emulieren)
  als Anzeige, dass die Figur aktiv gesendet wird.
- **OK lange halten** (in der Serien-Ansicht)  Serie als **Favorit** ⭐
  markieren / entfernen
- **Zurück**  Emulation stoppen / eine Ebene zurück / App verlassen

## Favoriten ⭐
Lieblingsserien werden **immer zuerst** gezeigt (mit ⭐), damit man nicht durch
alle 255 Serien blättern muss. Toggeln mit **langem OK** auf einer Serie.
Gespeichert in `SD:/apps_data/toniekids/favorites.txt` (eine Serie pro Zeile) —
kann auch am PC bearbeitet werden. Vorbelegt: **Bibi Blocksberg**, **Bibi & Tina**.

Neue Tonies erscheinen automatisch: `.nfc`-Dump in `nfc/Toniebox Figuren/<Serie>/`
legen (Bild optional).

## Bildaufbereitung
`tools/gen4.py` (aktuell): auf das Motiv **zuschneiden**, Motiv vom weißen
Hintergrund trennen und eine **schwarze Kontur** drumherum ziehen, Innenbereich
kräftig kontrastieren + **Atkinson-Dithering**, Größe **64×96 hochkant**. Die
Kontur macht die Figur klar erkennbar — auch **helle** Figuren (z. B. König der
Löwen, Elsa), die sonst fast weiß/unsichtbar wären. (`gen3.py` = Vorgänger ohne
Kontur.) Format `.fxbm`: 2 Byte Header `[B][H]`, dann XBM-Bitmap (LSB-first,
gesetztes Bit = schwarz), zeilenweise byte-aligned. Kontur-Vorschau:
`preview_kontur.png`.

## Icons neu erzeugen / erweitern (z. B. Englisch/Französisch)
```sh
python3 tools/genicons.py --dry   # Match gegen tonies.json -> matches.json
python3 tools/gen4.py             # Bilder mit Kontur -> icons_p/ (64x96)
python3 ~/.ufbt/current/scripts/storage.py -p /dev/ttyACM0 \
        send icons_p /ext/apps_data/toniekids/icons_p
```

## App neu bauen (ufbt / Momentum-SDK)
```sh
pip install --user ufbt
ufbt update --channel=dev --index-url=https://up.momentum-fw.dev/firmware/directory.json
cd src && ufbt          # baut dist/toniekids.fap
ufbt launch             # aufs Gerät + starten
```
Gegen das **Momentum-dev-SDK** bauen (passend zur Firmware, API 87.1).

## Wichtig beim Aktualisieren
Wenn die App gerade läuft, lädt der Loader die neue `.fap` erst nach **Schließen
und erneutem Öffnen**. Und: der Flipper muss zum Aufspielen **per USB verbunden**
sein.

## Status (verifiziert, headless über die Flipper-CLI)
`start series=255 icon_c=1 orient=vertical` (Hochformat + Bild lädt),
`emulate ok proto=SLIX` (direkte Emulation). 879 Hochformat-Icons auf dem Gerät
(612 echte Tonie-Bilder, 12 Symbol-Fallbacks, 255 Serien-Bilder).
Emulation an der echten Toniebox **läuft** (2026-07-03 bestätigt). Neu: LED-Blinken
(zyan) während der Emulation als sichtbare Rückmeldung — vorher blinkte nichts,
was fälschlich wie „keine Emulation" wirkte.
