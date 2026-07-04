#!/usr/bin/env python3
"""Holt die Spieldauer je Tonie von tonies.com und schreibt eine Nachschlage-Tabelle.

Ausgabe: durations.txt  ->  Zeilen "<Serie>/<Episode>.nfc\\t<Minuten>"
Schluessel = exakt der relative Pfad, den die App zur Laufzeit hat (aus matches.json).

Zuordnung: Statt Slugs blind zu raten, wird die **Produkt-Sitemap** von tonies.com geladen
(die echten Produkt-URLs). Jede Sammlungs-Folge wird ueber die Modellnummer (aus der Bild-URL
in matches.json) den offiziellen tonies.json-Namen zugeordnet, dann per Slug exakt bzw. per
Fuzzy-Match innerhalb derselben Serie auf eine echte URL abgebildet. Das hebt die Trefferquote
deutlich (Slug-Abweichungen bei Untertiteln/Kompilationen werden aufgeloest).

matches.json/tonies.json werden NICHT committet (s. .gitignore); dieses Skript ist regenerierbar.
"""
import json, re, sys, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
MATCHES = os.path.join(HERE, "matches.json")
TONIES = "/tmp/tonies.json"
OUT = os.path.join(HERE, "durations.txt")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SITEMAP = "https://tonies.com/sitemap.xml"

def slug(s):
    s = s.lower()
    for a, b in (("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss"),("&","und"),
                 ("é","e"),("è","e"),("á","a"),("à","a"),("â","a"),("ç","c")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status == 200:
                return r.read().decode("utf-8", "replace")
    except Exception:
        return None
    return None

def load_sitemap():
    """Alle de-de-Produkt-URLs -> exact{(sSlug,eSlug):url}, by_series{sSlug:[(eSlug,url)]}."""
    idx = get(SITEMAP) or ""
    maps = sorted(set(re.findall(r"https://tonies\.com/sitemap_products_\d+\.xml", idx)))
    urls = []
    for m in maps:
        xml = get(m) or ""
        urls += re.findall(r"https://tonies\.com/de-de/tonies/([^/]+)/([^/<]+)/?", xml)
    exact, by_series = {}, {}
    for sSlug, eSlug in urls:
        url = f"https://tonies.com/de-de/tonies/{sSlug}/{eSlug}/"
        exact[(sSlug, eSlug)] = url
        by_series.setdefault(sSlug, []).append((eSlug, url))
    return exact, by_series

def match_url(series, episode, exact, by_series):
    sSlug, eSlug = slug(series), slug(episode)
    if (sSlug, eSlug) in exact:
        return exact[(sSlug, eSlug)]
    cands = by_series.get(sSlug)
    if not cands and "/" in episode:  # Kompilation "A / B" -> erste Serie/Teil
        eSlug = slug(episode.split("/")[0])
        if (sSlug, eSlug) in exact:
            return exact[(sSlug, eSlug)]
    if not cands:
        return None
    et = set(t for t in eSlug.split("-") if t)
    best, best_score = None, 0.0
    for es, url in cands:
        st = set(t for t in es.split("-") if t)
        if not st:
            continue
        inter = len(et & st)
        union = len(et | st)
        score = inter / union if union else 0.0
        if es.startswith(eSlug) or eSlug.startswith(es):
            score = max(score, 0.92)
        if score > best_score:
            best_score, best = score, url
    return best if best_score >= 0.5 else None

def extract_minutes(html):
    if not html:
        return None
    m = re.findall(r"(\d{1,3})\s*Minuten", html)
    return int(m[0]) if m else None

def load_model_index():
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

def resolve(relpath, img_url, model_idx, exact, by_series):
    m = re.search(r"/(\d{2}-\d{4})-", img_url or "")
    if m and m.group(1) in model_idx:
        series, episode = model_idx[m.group(1)]
    else:
        parts = relpath.rsplit(".nfc", 1)[0].split("/", 1)
        series, episode = parts[0], (parts[1] if len(parts) > 1 else parts[0])
    url = match_url(series, episode, exact, by_series)
    if not url:
        return relpath, None
    return relpath, extract_minutes(get(url))

def main():
    matches = json.load(open(MATCHES))
    print("Sitemap laden ...", flush=True)
    exact, by_series = load_sitemap()
    print(f"Sitemap: {len(exact)} Produkt-URLs, {len(by_series)} Serien", flush=True)
    model_idx = load_model_index()
    print(f"Sammlung: {len(matches)} | tonies.json-Modelle: {len(model_idx)}", flush=True)
    results, done, matched = {}, 0, 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(resolve, rp, u, model_idx, exact, by_series): rp
                for rp, u in matches.items()}
        for fut in as_completed(futs):
            rp, mins = fut.result()
            done += 1
            if mins:
                results[rp] = mins; matched += 1
            if done % 60 == 0:
                print(f"  {done}/{len(matches)}, {matched} Treffer", flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for rp in sorted(results):
            f.write(f"{rp}\t{results[rp]}\n")
    print(f"FERTIG: {matched}/{len(matches)} Dauern -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
