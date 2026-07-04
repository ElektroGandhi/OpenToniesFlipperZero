#!/usr/bin/env python3
"""Holt die Spieldauer je Tonie von tonies.com und schreibt eine Nachschlage-Tabelle.

Ausgabe: durations.txt  ->  Zeilen "<Serie>/<Episode>.nfc\\t<Minuten>"
Schluessel = exakt der relative Pfad, den die App zur Laufzeit hat (aus matches.json).

Quelle der offiziellen Serien-/Episodennamen: tonies.json (via Modellnummer aus der
Bild-URL in matches.json). Fallback: die Ordner-/Dateinamen der Sammlung selbst.
tonies.json/matches.json werden NICHT ins Repo committet (s. .gitignore); dieses
Skript ist regenerierbar.
"""
import json, re, sys, time, os, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
MATCHES = os.path.join(HERE, "matches.json")
TONIES = "/tmp/tonies.json"  # lokal gecacht; sonst von der release-URL laden
OUT = os.path.join(HERE, "durations.txt")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
BASE = "https://tonies.com/de-de/tonies/"

def slug(s):
    s = s.lower()
    for a, b in (("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss"),("&","und"),
                 ("é","e"),("è","e"),("á","a"),("à","a"),("â","a"),("ç","c")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            if r.status == 200:
                return r.read().decode("utf-8", "replace")
    except Exception:
        return None
    return None

def extract_minutes(html):
    if not html:
        return None
    m = re.findall(r"(\d{1,3})\s*Minuten", html)
    return int(m[0]) if m else None

def load_tonies_model_index():
    if not os.path.exists(TONIES):
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/toniebox-reverse-engineering/"
            "tonies-json/release/tonies.json", TONIES)
    d = json.load(open(TONIES))
    idx = {}
    for e in d:
        mdl = (e.get("model") or "").strip()
        if mdl and e.get("series") and e.get("episodes"):
            idx.setdefault(mdl, (e["series"], e["episodes"]))
    return idx

def candidates(series, episode):
    """Slug-Kombinationen zum Ausprobieren (erste, die trifft, gewinnt)."""
    ss, es = slug(series), slug(episode)
    cands = [f"{ss}/{es}/"]
    # Kompilations-Titel "A / B" -> nur ersten Teil
    if "/" in episode:
        cands.append(f"{ss}/{slug(episode.split('/')[0])}/")
    # Episode ohne fuehrenden Serien-Praefix
    if episode.lower().startswith(series.lower()):
        rest = episode[len(series):].lstrip(" -_:").strip()
        if rest:
            cands.append(f"{ss}/{slug(rest)}/")
    # doppelte entfernen, Reihenfolge halten
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out

def resolve(relpath, url, model_idx):
    # offizielle Namen via Modellnummer aus der Bild-URL
    m = re.search(r"/(\d{2}-\d{4})-", url or "")
    if m and m.group(1) in model_idx:
        series, episode = model_idx[m.group(1)]
    else:
        parts = relpath.rsplit(".nfc", 1)[0].split("/", 1)
        series = parts[0]
        episode = parts[1] if len(parts) > 1 else parts[0]
    for cand in candidates(series, episode):
        mins = extract_minutes(fetch(BASE + cand))
        if mins:
            return relpath, mins, cand
        time.sleep(0.15)
    return relpath, None, None

def main():
    matches = json.load(open(MATCHES))
    model_idx = load_tonies_model_index()
    print(f"Sammlung: {len(matches)} | tonies.json-Modelle: {len(model_idx)}", flush=True)
    results, hits = {}, 0
    done = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(resolve, rp, url, model_idx): rp for rp, url in matches.items()}
        for fut in as_completed(futs):
            rp, mins, cand = fut.result()
            done += 1
            if mins:
                results[rp] = mins; hits += 1
            if done % 40 == 0:
                print(f"  {done}/{len(matches)} verarbeitet, {hits} Treffer", flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for rp in sorted(results):
            f.write(f"{rp}\t{results[rp]}\n")
    print(f"FERTIG: {hits}/{len(matches)} Dauern -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
