# OpenTonies – Projekt-Handover

> Übergabe an eine neue Session (mit Gitea-Zugang) zur Dokumentation/Veröffentlichung.
> Stand: 2026-07-03. Alle „verifiziert"-Aussagen wurden headless über die Flipper-CLI geprüft.

---

## 1. Was ist das?

**OpenTonies** ist eine selbst entwickelte **Flipper-Zero-App** (in C, als `.fap`),
die dem Kind erlaubt, **Tonie-Figuren grafisch auszuwählen und direkt zu emulieren**,
sodass die **Toniebox** die Figur erkennt und abspielt. Sie ist kinderfreundlich
(großes Bild pro Figur, Hochformat, Favoriten) und läuft auf **Momentum-Firmware**.

Kontext: Die Toniebox liest Tonie-Figuren per NFC (NXP **ICODE SLIX-L**, ISO15693).
Der Flipper kann diese Tags lesen und emulieren. OpenTonies bündelt eine ganze
Sammlung solcher Figuren-Dumps mit Bildern in einer bedienbaren Oberfläche.

---

## 2. Aktueller Stand (verifiziert)

| Feature | Status | Nachweis (diag/CLI) |
|---|---|---|
| App startet, liest Sammlung | ✅ | `start series=255` |
| Hochformat (64×128) | ✅ | `orient=vertical` |
| Bild pro Figur lädt (64×96) | ✅ | `icon_c=1` |
| Direkte SLIX-L-Emulation bei OK | ✅ | `emulate ok proto=SLIX file=…` |
| Favoriten zuerst + ⭐ | ✅ | `fav=2 first=Bibi Blocksberg` |
| Favorit an/aus per **langem OK** | ✅ | favorites.txt 2→3→2 im Test |
| Umbenannt in **OpenTonies** + „T"-Icon | ✅ | `loader info: "OpenTonies" is running` |
| Homescreen-Favorit (Momentum) gesetzt | ✅ (Datei) | `/ext/favorites.txt` → fap-Pfad |
| 879 Icons mit **dezenter Kontur** auf SD | ✅ | Icon vom Gerät byte-identisch zurückgelesen |

**Noch NICHT gerätetestbar (headless):** die tatsächliche Wiedergabe an der echten
Toniebox und die „Halten-zum-Starten"-Geste auf dem Homescreen. Beides muss der
Nutzer am Gerät bestätigen.

**Vorbelegte Favoriten:** `Bibi Blocksberg`, `Bibi & Tina`.

---

## 3. Hardware & Umgebung

- **Gerät:** Flipper Zero, verbunden als `/dev/ttyACM0` (CDC-Serial).
  ⚠️ Trennt sich beim Testen an der Box häufig — Port verschwindet dann.
- **Firmware:** **Momentum** `mntm-dev`, Commit **`8ed809fb`** (Build 2026-03-06),
  **API 87.1**, Target f7. (Nicht Unleashed — häufige Fehlannahme.)
- **Build:** `ufbt` mit **Momentum-dev-SDK** (exakt Commit `8ed809fb`, deshalb API-genau).
  Installation:
  ```sh
  pip install --user ufbt
  ufbt update --channel=dev --index-url=https://up.momentum-fw.dev/firmware/directory.json
  ```
- **Datei-Transfer:** `~/.ufbt/current/scripts/storage.py` (Flipper-RPC, robust, binärsicher).
  Braucht `pip install --user colorlog pyserial protobuf`.
- **Bildpipeline:** Python + **Pillow** (kein numpy nötig).
- **git:** 2.54.0 vorhanden; **kein `gh`**; user = `Antigravity Agent <agent@gigano.de>`.
  Kein Gitea-Remote in dieser Umgebung konfiguriert (→ Aufgabe der neuen Session).

---

## 4. Architektur (datengetrieben)

Die App hält **keine** eingebettete Figurenliste. Sie liest zur Laufzeit von der SD:

1. **Figuren/Struktur:** durchläuft Ordner `SD:/nfc/Toniebox Figuren/<Serie>/<Geschichte>.nfc`
   (255 Serien, 624 Figuren). Serie = Ordner, Geschichte = `.nfc`-Datei.
2. **Bilder:** lädt je Eintrag `SD:/apps_data/toniekids/icons_p/<Serie>/<Geschichte>.fxbm`
   (Serien-Übersicht: `_series.fxbm`). Format `.fxbm` = 2-Byte-Header `[Breite][Höhe]` +
   XBM-Bitmap (LSB-first, gesetztes Bit = schwarz), zeilenweise byte-aligned. Hier 64×96.
3. **Emulation:** bei OK → `nfc_device_load(<pfad>.nfc)` → `nfc_device_get_protocol/data`
   → `nfc_listener_alloc/start` (Protokoll **`NfcProtocolSlix`**, `SlixTypeSlixL`).
   Das ist exakt der Weg der eingebauten NFC-App.
4. **Favoriten:** App-Datei `SD:/apps_data/toniekids/favorites.txt` (eine Serie pro Zeile).
   Favoriten werden in der Serienliste **nach vorne** sortiert und mit ⭐ markiert.

**UI:** vertikale ViewPort-Orientierung (`ViewPortOrientationVertical` → 64×128).
Oben großes Bild, darunter Name + Zähler. Ebenen: Serie → Geschichte → „Spielt!".
Steuerung: alle Pfeilrichtungen navigieren (Halten = schnell, `InputTypeRepeat`);
**OK** = öffnen/abspielen; **langes OK** (Serien-Ebene) = Favorit toggeln; **Zurück** = zurück/stop.

**Wichtig – zwei verschiedene „favorites"-Dateien nicht verwechseln:**
- `SD:/apps_data/toniekids/favorites.txt` → **App-interne** Lieblingsserien (⭐, Sortierung).
- `SD:/favorites.txt` → **Momentum-Desktop-Favorit** (Homescreen-Schnellstart, enthält den
  fap-Pfad `/ext/apps/NFC/toniekids.fap`).

---

## 5. On-Device Dateien

```
SD:/apps/NFC/toniekids.fap                     # die App (Anzeigename „OpenTonies", 10164 B)
SD:/apps_data/toniekids/icons_p/<Serie>/*.fxbm # 879 Bilder (64×96, dezente Kontur)
SD:/apps_data/toniekids/favorites.txt          # App-Favoriten: "Bibi Blocksberg" / "Bibi & Tina"
SD:/apps_data/toniekids/diag.txt               # Diagnose (wird bei jedem Start überschrieben)
SD:/nfc/Toniebox Figuren/<Serie>/<...>.nfc     # 624 SLIX-L-Dumps (Drittquelle, s. u.)
SD:/favorites.txt                              # Momentum-Homescreen-Favorit → fap-Pfad
```
Reste eines Vorgänger-Layouts liegen ggf. noch als `icons/` (56×56) und `icons_s/` (32×32)
unter `apps_data/toniekids/` — werden **nicht** mehr genutzt, können gelöscht werden.

---

## 6. Repo-Struktur (lokal: `/home/blotto/tonie-box-app/`)

```
HANDOVER.md              # dieses Dokument
README.md                # Nutzer-/Bau-Doku
toniekids.fap            # gebautes Release (appid „toniekids", Name „OpenTonies")
src/
  toniekids.c            # kompletter App-Quellcode (C)
  application.fam        # Manifest (name="OpenTonies", fap_icon, fap_category=NFC)
  toniekids.png          # 10×10 App-Icon (Tonies-„T")
tools/
  gen4.py                # AKTUELLER Icon-Generator (Zuschnitt+Maske+Kontur+Atkinson, 64×96)
  genicons.py            # Matching der .nfc-Dateien gegen tonies.json (--dry) → matches.json
  matches.json           # Ergebnis: rel-Pfad → Bild-URL (612/624 Treffer) *(Drittquellen-URLs)*
  gen2.py, gen3.py       # Vorgänger-Generatoren (56/32 quer; 64×96 ohne Kontur) — Referenz
  gen_full.py            # allererster (64×64) — Referenz
  preview_*.py, portrait_preview.py  # Render-Vorschauen (dekodieren .fxbm / mocken Screen)
preview_*.png            # gerenderte Vorschauen (Design-Belege)
```

---

## 7. Build & Deploy

```sh
# Bauen (im src-Verzeichnis, gegen Momentum-dev-SDK)
cd src && ufbt                 # → dist/toniekids.fap

# Deployen + starten
ufbt launch                    # installiert nach /ext/apps/NFC/ und startet per Pfad

# Nur Datei-Transfer (App ODER Icons) ohne UI, robust:
ST=~/.ufbt/current/scripts/storage.py
python3 -u "$ST" -p /dev/ttyACM0 send dist/toniekids.fap /ext/apps/NFC/toniekids.fap
python3 -u "$ST" -p /dev/ttyACM0 send <icons_p-Ordner>   /ext/apps_data/toniekids/icons_p
```

---

## 8. Icon-Pipeline (Bilder erzeugen)

1. **Matching:** `python3 tools/genicons.py --dry` – normalisiert Serie/Geschichte,
   matcht gegen `tonies.json` (offene Tonie-DB), schreibt `matches.json` (rel → Bild-URL).
   Trefferquote 612/624 (98 %); 12 ohne Treffer bekommen ein Symbol-Fallback.
2. **Rendern:** `python3 tools/gen4.py` – lädt die Bilder (Cache), pro Bild:
   `autocrop` (aufs Motiv) → auf 64×96 einpassen → **Motiv-Maske** (Trennung vom weißen BG)
   → **1-px-Kontur auf der Silhouette** (`mask − erode(mask)`) → Innen: autocontrast +
   **Atkinson-Dithering** → als `.fxbm` packen. Ausgabe nach `icons_p/`.
   - Kontur-Stärke: ein Parameter (aktuell dezent, 1 px). Für dicker: `MaxFilter(mask)−mask`.
3. **Hochladen:** `storage.py send icons_p /ext/apps_data/toniekids/icons_p`.
   Neue Bilder erscheinen **ohne App-Neustart** (App lädt Icons pro Navigation).

Quelle der Bilder: `tonies.json` von
`raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/tonies.json`
(Feld `pic`). ⚠️ Bilder sind urheberrechtlich geschützt (s. §11).

---

## 9. Verifikation (headless, ohne Bildschirm)

Wir testen komplett über die Flipper-CLI auf `/dev/ttyACM0`:
- `loader open "<Name>"` / `loader info` / `loader close` – App starten/prüfen/beenden.
  ⚠️ `loader open` per **Name** findet frisch geschriebene externe faps oft nicht
  (`not found`) → stattdessen **`ufbt launch`** (startet per Pfad).
- `input send <up|down|left|right|ok|back> <short|long|repeat>` – Eingaben simulieren.
- `storage read/stat/list …` – Dateien lesen/prüfen.
- Die App schreibt beim Start eine **`diag.txt`**:
  `start series=<n> fav=<n> icon_c=<0|1> orient=vertical first=<Serie>` und pro Emulation
  `emulate ok proto=<Proto> file=<name>`. Das ist unser Hauptnachweis.
- Bilder prüfen: `storage.py receive <pfad> <lokal>` + `cmp` gegen die lokale `.fxbm`.

---

## 10. Der Weg hierher (Entscheidungen)

1. **Ausgangsproblem:** Die „Toniebox Figuren"-Sammlung auf dem Flipper bestand aus
   **0-Byte-Dateien** (kaputter Download aus `nortakales/flipper-zero-tonies`). Fix:
   echte SLIX-L-Dumps hochgeladen (624 DE, byte-verifiziert).
2. **App v1:** Querformat-Filmstrip (mittleres Bild 56×56 + Nachbarn 32×32).
   Kritik: Bilder zu klein/körnig.
3. **Bildqualität:** Ursachen erkannt – kein Zuschnitt (Figur winzig), Floyd-Steinberg
   zu körnig, zu klein. → **Zuschnitt + Atkinson**.
4. **Hochformat:** Idee des Nutzers – Flipper senkrecht (64×128), Bild 64×96. Tonie-Figuren
   sind hoch → deutlich besser erkennbar. `ViewPortOrientationVertical`.
5. **Favoriten:** Lieblingsserien zuerst + ⭐, Toggle per langem OK; Bibi vorbelegt.
6. **Kontur:** helle Figuren (König der Löwen, Elsa) verschwanden → **Maske + Kontur**.
   Zuerst 2 px (zu präsent) → auf Wunsch **1 px auf der Silhouette (dezent)**.
7. **Branding:** umbenannt in **OpenTonies**, 10×10-„T"-Icon, Momentum-Homescreen-Favorit.

---

## 11. ⚠️ Rechtliches – was NICHT ins Gitea gehört

Dieses Projekt berührt **urheberrechtlich geschütztes Fremdmaterial**. Ins öffentliche
(oder überhaupt ins) Repo gehört **nur der eigene Code + Werkzeuge + Doku**. **Nicht**
committen / veröffentlichen:

- **Tonie-NFC-Dumps** (`Toniebox Figuren/**/*.nfc`, das `flipper-zero-tonies`-Repo) —
  fremde Inhalte, nur referenzieren.
- **Die 879 Tonie-Bilder** (`icons_p/`, `icons/`, `icons_s/`) und der Bild-Cache
  (`imgcache/`, ~255 MB) — aus geschützten Produktbildern abgeleitet.
- **`tonies.json`** (vollständige DB, ~6 MB) — nur per URL referenzieren.
- `matches.json` enthält Titel→Bild-URLs (Drittquellen) — grenzwertig; im Zweifel
  weglassen oder als „regenerierbar" kennzeichnen.

Ins Repo gehören: `src/`, `tools/*.py`, `README.md`, `HANDOVER.md`, `toniekids.fap`
(eigene Binärdatei), die eigenen Vorschau-PNGs. Eine `.gitignore` (im Repo enthalten)
schließt die o. g. Artefakte aus. Bitte im Repo eine kurze **Rechtehinweis-/Disclaimer**-
und **LICENSE**-Datei ergänzen (Vorschlag: eigener Code unter MIT; klarer Hinweis, dass
Nutzer nur **eigene** Tonies spiegeln sollen und Bilder/Dumps nicht enthalten sind).

---

## 12. Bekannte Stolpersteine (Gotchas)

- **USB trennt sich beim Testen** → `/dev/ttyACM0` weg. Upload-Skripte auf Port warten
  lassen und mit Retry; **während** eines Transfers nicht parallel auf den Port zugreifen
  (RPC-Kollision: „multiple access on port").
- **`storage write_chunk` (rohe CLI) hängt an, statt zu überschreiben** → für rohe CLI-
  Schreibe erst `remove`. Deshalb nutzen wir **`storage.py`** (überschreibt sauber).
- **`pkill -f "storage.py"` killt die eigene Shell** (deren Cmdline enthält „storage.py"). Nie so.
- **`loader open <Name>`** findet frisch installierte externe faps oft nicht → `ufbt launch`.
- **Loader-Cache:** neue App taucht im „Add App"-Browser evtl. erst nach einmal
  Apps-Menü-Öffnen auf.
- **Läuft die App, wird die neue `.fap` erst nach Schließen+Öffnen geladen.**
- **Favoriten weg?** **Langes OK** toggelt — beide Bibis lassen sich so versehentlich
  entfernen (Datei wird dann leer). Wiederherstellen: `favorites.txt` mit den Serienzeilen
  neu senden + App neu starten.
- **appid ≠ Anzeigename:** intern bleibt alles `toniekids` (Pfade, Datenordner), angezeigt
  wird **OpenTonies**. Bewusst so, um die 879 Bilder + Favoriten nicht umziehen zu müssen.
- **Tool-Timeout:** der Bash-Tool-Default ist 2 Min — lange Uploads im Hintergrund fahren.

---

## 13. Offene Punkte / Next Steps

- [ ] **An echter Toniebox testen** (Wiedergabe) + **Homescreen-„Halten"-Geste** bestätigen
      (Einstellungen → Desktop → Favorite Apps zeigt die Taste).
- [ ] Optional **ins Hauptmenü** eintragen (nur am Gerät): UP → MNTM → Interface → Mainmenu →
      Add App → External App → `Apps/NFC/OpenTonies`.
- [ ] **Schwache Serien-Bilder** gezielt ersetzen (z. B. „Der kleine Drache Kokosnuss"
      = dunkles Cover). Ggf. pro Serie ein besseres Repräsentanz-Bild wählen.
- [ ] **EN/FR** Bilder ergänzen (Repo hat 114 EN + 12 FR; Pipeline identisch).
- [ ] Alte `icons/` + `icons_s/` vom Gerät entfernen (Speicher).
- [ ] Ggf. runderes/originalgetreueres „T"-Icon.

---

## 14. Auftrag an die Gitea-Session

1. **Repo anlegen** (z. B. `opentonies-flipper`) und den Inhalt von
   `/home/blotto/tonie-box-app/` gemäß `.gitignore` pushen (Code + tools + Doku + fap +
   Vorschauen; **keine** Bilder/Dumps/DB).
2. **README** ggf. für Gitea aufbereiten (Screenshots = die `preview_*.png`),
   `HANDOVER.md` als Entwickler-Doku übernehmen/verlinken.
3. **LICENSE** (Vorschlag MIT für eigenen Code) + **Rechtehinweis** (siehe §11) ergänzen.
4. Optional **Wiki**: Build/Deploy, Icon-Pipeline, Verifikation, Gotchas (aus §7–§12).
5. Diese Umgebung hat **kein** Gitea-Remote und **kein `gh`** — die Zugangsdaten/den
   Remote bringt deine Session mit. Ein lokaler Git-Stand (init + erster Commit) liegt
   bereits vor (siehe unten), du musst nur `git remote add` + `git push`.
```
