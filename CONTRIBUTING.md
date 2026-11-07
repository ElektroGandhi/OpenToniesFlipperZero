# Mitmachen · Contributing

**Deutsch** · [English](#english)

Schön, dass du helfen willst. Am wertvollsten sind gerade **Testberichte vom echten Gerät**, vor
allem zu Bluetooth und zu anderen Firmwares.

## Regeln

1. **Kein fremdes Material.** Keine `.nfc`-Dateien, Produktbilder oder Inhaltstexte. Die CI lehnt
   solche Dateien ab. Siehe [`NOTICE.md`](NOTICE.md).
2. **Nur behaupten, was lief.** „Kompiliert“ heißt nicht „funktioniert“. Schreib in den
   Pull-Request, was du wie an welchem Gerät geprüft hast.
3. **Beide READMEs pflegen.** `README.md` (Deutsch) und `README.en.md` (Englisch) bleiben
   inhaltlich gleich. `python3 tools/pruefe_repo.py` prüft das.

## Ablauf

```sh
git switch -c fix/mein-thema
cd src && ufbt                    # App bauen
cd .. && python3 tools/pruefe_repo.py
```

Danach einen Pull-Request öffnen. `CHANGELOG.md` bitte fortschreiben, der neueste Eintrag steht
oben.

## Spieldauern ergänzen

`tools/durations.txt` deckt etwa die Hälfte der Folgen ab. Je Zeile stehen
`<Serie>/<Datei>.nfc`, ein Tabulator und die Minuten. Ergänzungen sind per Pull-Request willkommen.

---

<a id="english"></a>

## English

Thanks for helping. The most valuable contribution right now is a **test report from a real
device**, especially on Bluetooth and other firmwares.

### Rules

1. **No third-party material.** No `.nfc` files, product images or content texts. CI rejects such
   files. See [`NOTICE.md`](NOTICE.md).
2. **Only claim what ran.** "It compiles" doesn't mean "it works". State in your pull request what
   you checked, how, and on which device.
3. **Keep both READMEs in step.** `README.md` (German) and `README.en.md` (English) stay identical
   in content. `python3 tools/pruefe_repo.py` checks this.

### Workflow

```sh
git switch -c fix/my-topic
cd src && ufbt                    # build the app
cd .. && python3 tools/pruefe_repo.py
```

Then open a pull request. Please update `CHANGELOG.md`, with the newest entry at the top.

### Adding running times

`tools/durations.txt` covers about half of the episodes. Each line holds `<Series>/<File>.nfc`, a
tab and the minutes. Additions are welcome as pull requests.
