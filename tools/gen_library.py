#!/usr/bin/env python3
"""Baut die Bibliothek fuer die Web-App: web/library.json (+ web/img/ Bildspiegel).

Quellen:
  * matches.json              -> "<Serie>/<Datei>.nfc" -> Bild-URL (= die eigene Sammlung)
  * tonies.json (GitHub)      -> Thema (category), offizieller Serien-/Episodenname, Trackliste
  * tonies.com Produkt-Sitemap-> echte Produkt-URLs
  * Produktseite              -> Inhaltstext ("Inhalt:") + Spieldauer

Zuordnung in drei Stufen, damit moeglichst wenig Folgen ohne Thema/Beschreibung bleiben:
  1. Modellnummer aus der Bild-URL (altes Format "01-0186-...")
  2. Serie + Episode exakt (normalisiert: Umlaute aufgeloest, Sonderzeichen weg)
  3. Fuzzy innerhalb derselben Serie (Jaccard >= 0.5), sonst fuzzy ueber die Serien-Namen

Bilder werden lokal gespiegelt (web/img/), damit die Web-App ohne fremdes CDN auskommt.

Aufruf:  python3 tools/gen_library.py [--no-images] [--limit N]
"""
import argparse, json, re, os, sys, tempfile, time, unicodedata, hashlib
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MATCHES = os.path.join(HERE, "matches.json")
DURATIONS = os.path.join(HERE, "durations.txt")
TONIES_CACHE = os.path.join(tempfile.gettempdir(), "tonies.json")
WEB = os.path.join(ROOT, "web")
IMGDIR = os.path.join(WEB, "img")
OUT = os.path.join(WEB, "library.json")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
SITEMAP = "https://tonies.com/sitemap.xml"
TONIES_URL = ("https://raw.githubusercontent.com/toniebox-reverse-engineering/"
              "tonies-json/release/tonies.json")

# tonies.json mischt englische Slugs und deutsche Klartext-Kategorien. Beides auf
# eine gemeinsame, kindgerechte Bezeichnung ziehen - sonst stehen "music" und
# "Musik" als zwei getrennte Themen nebeneinander.
THEME_MAP = {
    "audio-play": "Hörspiel",
    "hörspiele & hörbücher": "Hörspiel",
    "audio-book": "Hörbuch",
    "audio-play-songs": "Hörspiel mit Liedern",
    "audio-book-songs": "Hörbuch mit Liedern",
    "music": "Musik",
    "musik": "Musik",
    "audio-play-educational": "Wissen",
    "wissen": "Wissen",
    "sleep": "Einschlafen",
    "schlaflieder": "Einschlafen",
}
THEME_FALLBACK = "Sonstiges"


def norm(s):
    """Vergleichsform: klein, Umlaute aufgeloest, nur Buchstaben/Ziffern/Leerzeichen."""
    s = (s or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("&", "und"),
                 ("é", "e"), ("è", "e"), ("á", "a"), ("à", "a"), ("â", "a"), ("ç", "c")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", norm(s))).strip("-")


def jaccard(a, b):
    A, B = set(a.split()), set(b.split())
    return len(A & B) / len(A | B) if (A | B) else 0.0


def get(url, timeout=30, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200:
                return None
            raw = r.read()
            return raw if binary else raw.decode("utf-8", "replace")
    except Exception:
        return None


# ---------- Quellen laden ----------
def load_tonies():
    # Ein abgebrochener Download hat sonst dauerhaft eine halbe Datei
    # zurueckgelassen; der naechste Aufruf las sie ungeprueft und warf
    # JSONDecodeError, ohne jemals neu zu laden.
    def _hole_und_pruefe():
        tmp = TONIES_CACHE + ".tmp"
        urllib.request.urlretrieve(TONIES_URL, tmp)
        json.load(open(tmp))                 # wirft, wenn der Inhalt kaputt ist
        os.replace(tmp, TONIES_CACHE)
    if not os.path.exists(TONIES_CACHE):
        _hole_und_pruefe()
    try:
        return json.load(open(TONIES_CACHE))
    except (json.JSONDecodeError, ValueError):
        try: os.remove(TONIES_CACHE)
        except OSError: pass
        _hole_und_pruefe()
        return json.load(open(TONIES_CACHE))


def load_sitemap():
    """Alle de-de-Produkt-URLs -> exact{(sSlug,eSlug):url}, by_series{sSlug:[(eSlug,url)]}."""
    idx = get(SITEMAP) or ""
    maps = sorted(set(re.findall(r"https://tonies\.com/sitemap_products_\d+\.xml", idx)))
    exact, by_series = {}, {}
    for m in maps:
        xml = get(m) or ""
        for s_slug, e_slug in re.findall(
                r"https://tonies\.com/de-de/tonies/([^/]+)/([^/<]+?)/?<", xml):
            url = f"https://tonies.com/de-de/tonies/{s_slug}/{e_slug}/"
            exact[(s_slug, e_slug)] = url
            by_series.setdefault(s_slug, []).append((e_slug, url))
    return exact, by_series


def eigene_sammlung():
    """Alles, was zur Sammlung gehoert: {relpath -> Bild-URL oder None}.

    ⚠️ NICHT nur matches.json. `update_tonies.py` legt neue Dumps unter
    tools/tonies_repo/ ab, und **niemand schreibt matches.json je fort** — wer
    nur dort nachsieht, erzeugt eine Bibliothek ohne die frisch geholten Folgen.
    Genau daran lief die beworbene Kette update_tonies -> gen_library ins Leere:
    zwei Laeufe hintereinander meldeten unveraendert "NEU: 40", und die neuen
    Folgen erreichten die Web-App nie.

    Dumps ohne Eintrag in matches.json haben hier None als Bild-URL; sie wird
    spaeter aus dem `pic`-Feld von tonies.json nachgezogen.
    """
    aus = dict(json.load(open(MATCHES))) if os.path.exists(MATCHES) else {}
    lager = os.path.join(HERE, "tonies_repo")
    dazu = 0
    if os.path.isdir(lager):
        for wurzel, _, dateien in os.walk(lager):
            for fn_ in dateien:
                if not fn_.endswith(".nfc"):
                    continue
                rel = os.path.relpath(os.path.join(wurzel, fn_), lager)
                if rel not in aus:
                    aus[rel] = None
                    dazu += 1
    if dazu:
        print(f"  aus tools/tonies_repo/ dazu: {dazu} (Bild kommt aus tonies.json)",
              flush=True)
    return aus


def load_durations():
    d = {}
    if os.path.exists(DURATIONS):
        for line in open(DURATIONS, encoding="utf-8"):
            rel, _, mins = line.rstrip("\n").partition("\t")
            if rel and mins.isdigit():
                d[rel] = int(mins)
    return d


# ---------- Zuordnung Sammlung -> tonies.json ----------
class ToniesIndex:
    def __init__(self, tonies):
        self.by_model = {}
        self.exact = {}
        self.by_series = {}
        for e in tonies:
            mdl = (e.get("model") or "").strip()
            if mdl:
                self.by_model.setdefault(mdl, e)
            if not (e.get("language") or "").startswith("de"):
                continue
            s, ep = norm(e.get("series")), norm(e.get("episodes"))
            if s and ep:
                self.exact.setdefault((s, ep), e)
                self.by_series.setdefault(s, []).append((ep, e))
        self.series_keys = list(self.by_series)

    def lookup(self, relpath, img_url):
        """(eintrag, stufe) - stufe dokumentiert, wie sicher der Treffer ist."""
        m = re.search(r"/(\d{2}-\d{4})-", img_url or "")
        if m and m.group(1) in self.by_model:
            return self.by_model[m.group(1)], "modell"

        # Drei Ebenen (Book Tonies/Conni/Folge.nfc): die Serie ist der innere Ordner.
        teile = relpath.split("/")
        series, fn = teile[-2] if len(teile) > 1 else "", teile[-1]
        ep = fn[:-4] if fn.endswith(".nfc") else fn
        s, e = norm(series), norm(ep)

        if (s, e) in self.exact:
            return self.exact[(s, e)], "exakt"

        cands = self.by_series.get(s)
        if not cands:
            # Serienname weicht ab ("Wieso Weshalb Warum" vs "Wieso? Weshalb? Warum?")
            best_s, best_score = None, 0.0
            for key in self.series_keys:
                sc = jaccard(s, key)
                if sc > best_score:
                    best_score, best_s = sc, key
            if best_score >= 0.6:
                cands = self.by_series.get(best_s)
        if not cands:
            return None, "fehlt"

        best, best_score = None, 0.0
        for cand_ep, entry in cands:
            sc = jaccard(e, cand_ep)
            if len(e) >= 6 and (cand_ep.startswith(e) or e.startswith(cand_ep)):
                sc = max(sc, 0.92)
            if sc > best_score:
                best_score, best = sc, entry
        if best_score >= 0.5:
            return best, "fuzzy"
        return None, "fehlt"


def match_url(series, episode, exact, by_series):
    s_slug = slug(series)
    variants = [slug(episode)]
    if "/" in episode:
        variants.append(slug(episode.split("/")[0]))
    for e_slug in variants:
        if (s_slug, e_slug) in exact:
            return exact[(s_slug, e_slug)]
    cands = by_series.get(s_slug)
    if not cands:
        return None
    best, best_score = None, 0.0
    for e_slug in variants:
        for cand, url in cands:
            sc = jaccard(e_slug.replace("-", " "), cand.replace("-", " "))
            if len(e_slug) >= 6 and (cand.startswith(e_slug) or e_slug.startswith(cand)):
                sc = max(sc, 0.92)
            if sc > best_score:
                best_score, best = sc, url
    return best if best_score >= 0.5 else None


# ---------- Produktseite auswerten ----------
DESC_RE = re.compile(
    r'ExpandableProductDescription_wrapper.*?data-testid="paragraph"[^>]*>\s*<span>(.*?)</span>',
    re.S)


def clean_html(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
          .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
          .replace("„", "„").replace("&shy;", ""))
    return re.sub(r"\s+", " ", s).strip()


def scrape(url):
    """(beschreibung, minuten) von der Produktseite; beides kann None sein."""
    html = get(url)
    if not html:
        return None, None
    m = DESC_RE.search(html)
    desc = clean_html(m.group(1)) if m else None
    if desc and len(desc) < 25:
        desc = None
    # Die Laufzeit steht in der Produktseite als JSON-Schablone
    # "runTime":"ca. 42 Minuten" — die freie Suche nach "N Minuten" trifft
    # dagegen ins Leere, weil das eingebettete Skript nur eine Platzhalter-
    # Vorlage rendert. Einen Zahl aus dem echten runTime-Feld ziehen.
    mins = None
    m2 = re.search(r'"runTime"\s*:\s*"[^"]*?(\d{1,3})\s*Minuten', html)
    if m2:
        v = int(m2.group(1))
        if 3 <= v <= 400:                    # Plausibilitaet
            mins = v
    return desc, mins


# ---------- Bildspiegel ----------
# Die Produktfotos sind Shop-Aufloesung (in Summe ~255 MB). Auf dem Telefon wird
# jedes Bild als Kachel gezeigt - IMG_MAX Pixel Kantenlaenge reichen dafuer, und
# erst damit ist die Bibliothek ueber WLAN ueberhaupt benutzbar.
IMG_MAX = 400
IMG_QUALITY = 80
IMG_PAD = 0.04       # Luft rund um das Motiv, damit nichts den Rand beruehrt
WHITE_BG = 238       # ab hier gilt ein Pixel als Hintergrundweiss
WHITE_SOFT = 205     # Halbschatten-Band fuer eine weiche Kante


def _strip_white(im):
    """Zusammenhaengendes Weiss VOM RAND HER durchsichtig machen.

    Rund 5 % der Produktfotos sind nicht freigestellt, sondern vor weissem
    Studiohintergrund aufgenommen. Auf der Kachel steht dann ein weisser Kasten
    — im Dunkelmodus besonders haesslich.

    Nur vom Rand her: Weiss MITTEN im Motiv (Augen, Schrift auf einem Cover)
    bleibt unangetastet. Rueckgabe (bild, entfernter_anteil).
    """
    import numpy as np
    from PIL import Image

    a = np.array(im.convert("RGBA"))
    h, w = a.shape[:2]
    rgb = a[:, :, :3].astype(np.int16)
    light = (rgb.min(axis=2) >= WHITE_BG) & (a[:, :, 3] > 0)
    clear = a[:, :, 3] == 0

    grow = clear.copy()
    grow[0, :] |= light[0, :]; grow[-1, :] |= light[-1, :]
    grow[:, 0] |= light[:, 0]; grow[:, -1] |= light[:, -1]
    while True:
        nxt = grow.copy()
        nxt[1:, :] |= grow[:-1, :]
        nxt[:-1, :] |= grow[1:, :]
        nxt[:, 1:] |= grow[:, :-1]
        nxt[:, :-1] |= grow[:, 1:]
        nxt &= (light | clear)
        if np.array_equal(nxt, grow):
            break
        grow = nxt
    removed = grow & light
    frac = removed.sum() / max(1, a.shape[0] * a.shape[1])

    out = a.copy()
    out[:, :, 3] = np.where(removed, 0, out[:, :, 3])

    # Weiche Kante: helle Pixel direkt am Schnitt teildurchsichtig machen,
    # sonst bleibt ein harter weisser Saum um die Figur.
    edge = np.zeros((h, w), bool)
    edge[1:, :] |= removed[:-1, :]; edge[:-1, :] |= removed[1:, :]
    edge[:, 1:] |= removed[:, :-1]; edge[:, :-1] |= removed[:, 1:]
    edge &= ~removed
    band = edge & (rgb.min(axis=2) >= WHITE_SOFT)
    if band.any():
        v = rgb.min(axis=2)[band].astype("float32")
        out[:, :, 3][band] = np.clip(
            (WHITE_BG - v) / (WHITE_BG - WHITE_SOFT) * 255, 0, 255).astype("uint8")
    return Image.fromarray(out), frac


def _has_white_border(im):
    """Hat das Bild ueberhaupt einen deckenden hellen Rand?

    Rund 95 % der Produktfotos sind bereits freigestellt. Die anzufassen ist
    nicht nur unnoetig, sondern gefaehrlich: der Flood-Fill waechst auch aus
    durchsichtigen Bereichen heraus und frisst sich dann in helle Figuren
    (Lars der Eisbaer, Olaf). Deshalb vorher fragen, statt hinterher zu heilen.
    """
    import numpy as np
    a = np.array(im.convert("RGBA"))
    h, w = a.shape[:2]
    ecken = (a[0, 0], a[0, w - 1], a[h - 1, 0], a[h - 1, w - 1])
    return sum(1 for c in ecken if c[3] > 200 and c[:3].min() >= WHITE_BG) >= 3


def _opaque_share(im):
    """Anteil deckender Flaeche an der Bounding-Box. Cover fuellen sie fast ganz."""
    import numpy as np
    al = np.array(im.convert("RGBA"))[:, :, 3]
    ys, xs = np.nonzero(al > 16)
    if len(ys) == 0:
        return 0.0
    box = al[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return float((box > 16).sum()) / box.size


def _fray(im):
    """Randanteil der Silhouette — wie zerfranst ist das Motiv?

    Bei einer weissen Figur vor weissem Grund gibt es keine Kante, an der der
    Flood-Fill stoppt: er frisst sich ins Motiv und laesst Streifen zurueck.
    Eine kompakte Figur hat wenig Rand je Flaeche, eine zerfressene viel.
    Nachgemessen an bekannten Faellen (400x400): zerfressen 0,065-0,116
    (Lars der Eisbaer, Pummeleinhorn), heil 0,032-0,058 (Olaf, Astronaut).
    """
    import numpy as np
    m = np.array(im.convert("RGBA"))[:, :, 3] > 16
    if m.sum() == 0:
        return 1.0
    inner = m.copy()
    inner[1:, :] &= m[:-1, :]; inner[:-1, :] &= m[1:, :]
    inner[:, 1:] &= m[:, :-1]; inner[:, :-1] &= m[:, 1:]
    return float((m & ~inner).sum()) / m.sum()


FRAY_MAX = 0.060   # darueber gilt das Freistellen als misslungen


def _trim_and_center(im, size=IMG_MAX):
    """Auf das Motiv zuschneiden und mittig auf eine quadratische Leinwand setzen.

    Damit sind alle Figuren im Regal gleich gross — eine gemeinsame
    Bounding-Box. Ohne das wirkt jede Reihe unruhig.
    """
    import numpy as np
    from PIL import Image

    a = np.array(im.convert("RGBA"))
    ys, xs = np.nonzero(a[:, :, 3] > 16)
    if len(ys) == 0:
        return im
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    inner = int(size * (1 - 2 * IMG_PAD))
    im.thumbnail((inner, inner), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return canvas


def mirror_image(url):
    """Bild lokal ablegen und verkleinern (WebP), damit die Web-App ohne fremdes CDN
    auskommt und nicht hunderte MB laedt. -> Dateiname oder None."""
    if not url:
        return None
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".webp"
    dest = os.path.join(IMGDIR, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return name
    data = get(url, binary=True)
    if not data:
        return None
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        # Erst verkleinern, dann freistellen: der Flood-Fill braucht so viele
        # Durchlaeufe wie das Bild breit ist — auf Shop-Aufloesung dauert das
        # Sekunden je Bild, auf 400 px Millisekunden.
        im.thumbnail((IMG_MAX, IMG_MAX), Image.LANCZOS)

        # Freistellen nur, wenn es nachweislich gutgegangen ist. Ein Bild mit
        # weissem Grund ist ein Schoenheitsfehler, eine zerfressene Figur ein
        # Datenschaden — im Zweifel also nichts anfassen.
        out = None
        if _has_white_border(im):          # schon freigestellte Bilder gar nicht anfassen
            stripped, frac = _strip_white(im)
            if frac >= 0.02:
                share = _opaque_share(stripped)
                if 0.04 <= share <= 0.90:  # weder Cover noch fast alles weg
                    cand = _trim_and_center(stripped)
                    if _fray(cand) <= FRAY_MAX:   # zweites Netz: nicht zerfranst
                        out = cand
        if out is None:
            out = _trim_and_center(im)
        out.save(dest, "WEBP", quality=IMG_QUALITY, method=4)
    except Exception as exc:
        print(f"  Bild-Fehler {url[:60]}: {exc}", flush=True)
        return None
    return name


def main():
    # Ohne argparse hat `--help` den vollen Lauf gestartet und `--limit` ohne
    # Wert einen nackten Traceback geworfen. Beides ist jetzt Fehler mit Hilfe.
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-images", action="store_true",
                    help="Bilder nicht mitspiegeln (schneller Lauf)")
    ap.add_argument("--limit", type=int, default=None, metavar="N",
                    help="nur die ersten N Folgen bauen (fuer schnelle Tests)")
    args = ap.parse_args()
    no_images = args.no_images
    limit = args.limit

    os.makedirs(IMGDIR, exist_ok=True)
    matches = eigene_sammlung()
    items_in = sorted(matches.items())
    if limit:
        items_in = items_in[:limit]

    print(f"Sammlung: {len(items_in)} Folgen", flush=True)
    print("tonies.json laden ...", flush=True)
    index = ToniesIndex(load_tonies())
    print(f"  {len(index.by_series)} deutsche Serien indiziert", flush=True)
    print("Sitemap laden ...", flush=True)
    exact, by_series = load_sitemap()
    print(f"  {len(exact)} Produkt-URLs, {len(by_series)} Serien", flush=True)
    durations = load_durations()
    print(f"durations.txt: {len(durations)} bekannte Spieldauern", flush=True)

    def build(rel, img_url):
        entry, stage = index.lookup(rel, img_url)
        if not img_url and entry:
            # Frisch geholter Dump ohne Eintrag in matches.json: das Bild steht
            # im `pic`-Feld der Tonie-Datenbank.
            img_url = (entry.get("pic") or "").strip() or None
        teile = rel.split("/")
        path_series, fn = teile[-2] if len(teile) > 1 else "", teile[-1]
        path_ep = fn[:-4] if fn.endswith(".nfc") else fn

        series = (entry.get("series") if entry else None) or path_series
        episode = (entry.get("episodes") if entry else None) or path_ep
        raw_cat = (entry.get("category") if entry else None) or ""
        theme = THEME_MAP.get(raw_cat.strip().lower(), None)
        tracks = [t for t in (entry.get("tracks") if entry else []) or [] if t]

        url = match_url(series, episode, exact, by_series)
        desc, mins = scrape(url) if url else (None, None)

        if theme is None:
            theme = THEME_FALLBACK
        local_img = None if no_images else mirror_image(img_url)

        return {
            "path": rel,                       # exakt der Pfad, den der Flipper kennt
            "series": series,
            "episode": episode,
            "theme": theme,
            "desc": desc,
            "tracks": tracks,
            "minutes": durations.get(rel) or mins,
            "img": local_img,
            "img_url": img_url,
            "url": url,
            "match": stage,
        }

    out, done, fehler = [], 0, 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(build, rel, url): rel for rel, url in items_in}
        for fut in as_completed(futs):
            try:
                out.append(fut.result())
            except Exception as exc:
                fehler += 1
                print(f"  FEHLER bei {futs[fut]}: {exc}", flush=True)
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(items_in)} ({time.time()-t0:.0f}s)", flush=True)

    # Eingangs- gegen Ausgangszahl: ein still verlorener Worker haette sonst
    # nur eine niedrigere Zahl in der Bilanz, nichts weiter.
    if len(out) != len(items_in):
        print(f"\nFEHLER: {len(items_in)-len(out)} Folgen fehlen in der Ausgabe"
              f" ({fehler} Worker-Fehler). library.json wird NICHT geschrieben.",
              flush=True)
        sys.exit(1)

    # ⚠️ Vorhandene Vorlese-Verknuepfungen UEBERNEHMEN. Ohne das verwaist jeder
    # Bibliotheks-Neubau alle MP3 unter web/tts/: die Dateien bleiben liegen,
    # aber kein Eintrag zeigt mehr darauf, und die App faellt STUMM auf die
    # Browserstimme zurueck. Nichts bricht — es klingt nur schlechter, und
    # niemand merkt warum.
    if os.path.exists(OUT):
        try:
            alt_doc = json.load(open(OUT, encoding="utf-8"))
            alt_tts = {i["path"]: i.get("tts") for i in alt_doc.get("items", []) if i.get("tts")}
            uebernommen = 0
            for d in out:
                if not d.get("tts") and alt_tts.get(d["path"]):
                    d["tts"] = alt_tts[d["path"]]
                    uebernommen += 1
            if uebernommen:
                print(f"  Vorlese-Dateien uebernommen: {uebernommen}", flush=True)
        except Exception as exc:
            print(f"  WARNUNG: alte library.json nicht lesbar ({exc}) — "
                  "tts-Felder gehen verloren, danach gen_vorlesen.py laufen lassen", flush=True)

    out.sort(key=lambda d: (d["theme"], norm(d["series"]), norm(d["episode"])))
    themes = sorted({d["theme"] for d in out})
    doc = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "count": len(out),
        "themes": themes,
        "items": out,
    }
    os.makedirs(WEB, exist_ok=True)
    # Atomar: .tmp schreiben, dann umbenennen. Ein abgebrochener Lauf laesst
    # sonst eine halbe library.json zurueck, die die Web-App leer sieht.
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)

    # Ehrliche Abdeckungs-Bilanz: was fehlt, faellt sonst erst in der Web-App auf.
    with_desc = sum(1 for d in out if d["desc"])
    with_mins = sum(1 for d in out if d["minutes"])
    with_img = sum(1 for d in out if d["img"])
    themed = sum(1 for d in out if d["theme"] != THEME_FALLBACK)
    stages = {}
    for d in out:
        stages[d["match"]] = stages.get(d["match"], 0) + 1
    print(f"\nFERTIG -> {OUT}")
    print(f"  Folgen        : {len(out)}")
    print(f"  Thema erkannt : {themed}  ({100*themed//max(1,len(out))} %)")
    print(f"  Beschreibung  : {with_desc}  ({100*with_desc//max(1,len(out))} %)")
    print(f"  Spieldauer    : {with_mins}  ({100*with_mins//max(1,len(out))} %)")
    print(f"  Bild lokal    : {with_img}")
    print(f"  Zuordnung     : {stages}")
    print(f"  Themen        : {themes}")


if __name__ == "__main__":
    main()
