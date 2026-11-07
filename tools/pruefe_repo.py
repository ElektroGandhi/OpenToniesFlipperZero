#!/usr/bin/env python3
"""Repo-Prüfung, auch in der CI: kein Fremdmaterial, beide READMEs im Gleichschritt.

    python3 tools/pruefe_repo.py          # Rückgabe 0 = bestanden, 1 = durchgefallen
    python3 tools/pruefe_repo.py --selbsttest

Die READMEs werden an ihrer Struktur verglichen: gleich viele Überschriften je Ebene,
Tabellenzeilen, Code-Blöcke, Bilder, und dieselben Link-Ziele. Inhalte kann ein Skript
nicht übersetzen, aber ein vergessener Abschnitt oder eine fehlende Zeile fällt auf.
"""
import os, re, subprocess, sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERBOTEN = re.compile(
    r"\.nfc$|(^|/)web/img/|(^|/)web/tts/|(^|/)web/library\.json$|tonies_repo/|(^|/)tonies\.json$"
    r"|(^|/)matches\.json$|(^|/)icons[^/]*/|(^|/)favorites\.txt$|\.fap$",
    re.I,
)
PRIVAT = re.compile(r"192\.168\.178\.|gigano\.de|/mnt/user/|/home/blotto|/tmp/claude-|ssh unraid", re.I)
# Dieses Skript nennt die Muster selbst; die Historie im CHANGELOG ist kein Fund.
PRIVAT_AUSNAHMEN = {"tools/pruefe_repo.py"}


def dateien():
    aus = subprocess.check_output(["git", "ls-files", "-z"], cwd=WURZEL).decode()
    return [f for f in aus.split("\0") if f and os.path.exists(os.path.join(WURZEL, f))]


def struktur(text):
    ohne_code = re.sub(r"```.*?```", "", text, flags=re.S)
    return {
        "Überschrift 1": len(re.findall(r"^# ", ohne_code, re.M)),
        "Überschrift 2": len(re.findall(r"^## ", ohne_code, re.M)),
        "Tabellenzeilen": len(re.findall(r"^\|", ohne_code, re.M)),
        "Listenpunkte": len(re.findall(r"^- ", ohne_code, re.M)),
        "Code-Blöcke": text.count("```") // 2,
        "Bilder": sorted(re.findall(r'<img src="(?!https://img\.shields)([^"]+)"', text)),
        "Links": sorted(
            l
            for l in re.findall(r"\]\((https?://[^)]+|[^)#][^)]*)\)", ohne_code)
            + re.findall(r'href="(https?://[^"]+)"', ohne_code)
            if not l.startswith("README")
        ),
    }


def vergleiche(de, en):
    return [
        f"README: {k} weicht ab: {de[k]!r} / {en[k]!r}" for k in de if de[k] != en[k]
    ]


def fehlende_links(pfad, text):
    aus = []
    for ziel in re.findall(r"\]\(([^)#:]+)(?:#[^)]*)?\)", re.sub(r"```.*?```", "", text, flags=re.S)):
        if not os.path.exists(os.path.join(WURZEL, ziel)):
            aus.append(f"{pfad}: Link-Ziel fehlt: {ziel}")
    return aus


def pruefen():
    fehler, alle = [], dateien()
    for f in alle:
        if VERBOTEN.search(f):
            fehler.append(f"Fremdmaterial oder Binärdatei im Repo: {f}")
        if f in PRIVAT_AUSNAHMEN or f == "CHANGELOG.md" or f.endswith((".woff2", ".png", ".gif", ".mp4")):
            continue
        try:
            with open(os.path.join(WURZEL, f), encoding="utf-8") as d:
                inhalt = d.read()
        except UnicodeDecodeError:
            continue
        if PRIVAT.search(inhalt):
            fehler.append(f"Privater Pfad oder interne Adresse: {f}")
    lies = lambda p: open(os.path.join(WURZEL, p), encoding="utf-8").read()
    de, en = lies("README.md"), lies("README.en.md")
    fehler += vergleiche(struktur(de), struktur(en))
    fehler += fehlende_links("README.md", de) + fehlende_links("README.en.md", en)
    if "README.en.md" not in de or 'href="README.md"' not in en:
        fehler.append("README: Sprachumschalter fehlt")
    for f in ("demo.gif", "demo.mp4", "banner.png", "screens.png", "web.png"):
        if not os.path.exists(os.path.join(WURZEL, "docs/media", f)):
            fehler.append(f"Medium fehlt: docs/media/{f}")
    return fehler


def selbsttest():
    """Das Messgerät am Fehlerfall prüfen: es muss jeden dieser Fälle bemerken."""
    a = "# T\n## A\n| x |\n- p\n[l](http://a)\n"
    assert not vergleiche(struktur(a), struktur(a))
    assert vergleiche(struktur(a), struktur(a + "## B\n"))
    assert vergleiche(struktur(a), struktur(a + "| y |\n"))
    assert vergleiche(struktur(a), struktur(a.replace("http://a", "http://b")))
    for name in ("x/a.nfc", "web/library.json", "icons_p/a.fxbm", "A.NFC", "tools/matches.json"):
        assert VERBOTEN.search(name), name
    assert not VERBOTEN.search("src/toniekids.c")
    assert PRIVAT.search("http://192.168.178.48") and not PRIVAT.search("http://192.168.1.100")
    print("Selbsttest bestanden")


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        selbsttest()
        sys.exit(0)
    befunde = pruefen()
    for b in befunde:
        print("✗", b)
    print("DURCHGEFALLEN" if befunde else "BESTANDEN")
    sys.exit(1 if befunde else 0)
