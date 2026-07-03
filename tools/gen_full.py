#!/usr/bin/env python3
import os, sys, json, hashlib, io, time, urllib.request
from PIL import Image, ImageOps, ImageDraw, ImageFont

BASE = "/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad"
LOCAL = BASE + "/flipper-zero-tonies-master/German"
OUT = BASE + "/icons"
CACHE = BASE + "/imgcache"
MATCHES = BASE + "/matches.json"
LOG = BASE + "/gen_full.log"
W = H = 64
UA = "Mozilla/5.0 (icon-fetch)"

os.makedirs(OUT, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
def log(m):
    with open(LOG, "a") as f: f.write(m + "\n")
    print(m, flush=True)

def fetch(url):
    h = hashlib.md5(url.encode()).hexdigest()
    cp = os.path.join(CACHE, h)
    if os.path.exists(cp):
        with open(cp, "rb") as f: return f.read()
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=15).read()
            with open(cp, "wb") as f: f.write(data)
            return data
        except Exception as e:
            if attempt == 1:
                return None
            time.sleep(0.3)
    return None

def to_fxbm(img):
    # img: PIL Image -> 64x64 1-bit, packed XBM LSB-first, prefixed [W,H]
    img = img.convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(bg, img).convert("L")
    img = ImageOps.autocontrast(img, cutoff=2)
    img.thumbnail((W, H), Image.LANCZOS)
    canvas = Image.new("L", (W, H), 255)
    canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
    bw = canvas.convert("1")  # Floyd-Steinberg dither
    px = bw.load()
    out = bytearray([W, H])
    for y in range(H):
        for bxo in range(W // 8):
            b = 0
            for bit in range(8):
                if px[bxo * 8 + bit, y] == 0:  # schwarz -> Vordergrund
                    b |= (1 << bit)
            out.append(b)
    return bytes(out), bw

def get_font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

def fallback(series):
    im = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, W - 3, H - 3], radius=8, outline=0, width=2)
    words = [w for w in series.replace("-", " ").split() if w]
    initials = "".join(w[0] for w in words[:3]).upper() or series[:2].upper()
    f = get_font(30)
    try:
        bb = d.textbbox((0, 0), initials, font=f); tw = bb[2]-bb[0]; th = bb[3]-bb[1]
        d.text(((W - tw) // 2 - bb[0], (H - th) // 2 - bb[1]), initials, font=f, fill=0)
    except Exception:
        d.text((14, 24), initials, fill=0)
    bw = im.convert("1")
    px = bw.load()
    out = bytearray([W, H])
    for y in range(H):
        for bxo in range(W // 8):
            b = 0
            for bit in range(8):
                if px[bxo * 8 + bit, y] == 0: b |= (1 << bit)
            out.append(b)
    return bytes(out)

def ascii_preview(bw):
    px = bw.load()
    lines = []
    for y in range(0, H, 2):
        row = "".join("#" if px[x, y] == 0 else " " for x in range(0, W, 1))
        lines.append(row)
    return "\n".join(lines)

def main():
    matches = json.load(open(MATCHES))
    open(LOG, "w").close()
    # local files
    items = []
    for root, _, files in os.walk(LOCAL):
        for fn in files:
            if fn.endswith(".nfc"):
                rel = os.path.relpath(os.path.join(root, fn), LOCAL)
                items.append(rel)
    items.sort()
    log(f"icons zu erzeugen: {len(items)}")
    made = fb = 0; preview_done = False
    series_rep = {}  # series -> fxbm bytes (repraesentativ)
    for i, rel in enumerate(items, 1):
        parts = rel.split(os.sep)
        series = parts[0]
        outpath = os.path.join(OUT, rel[:-4] + ".fxbm")  # ".nfc"->".fxbm"
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        data = None; is_real = False
        url = matches.get(rel)
        if url:
            raw = fetch(url)
            if raw:
                try:
                    img = Image.open(io.BytesIO(raw))
                    data, bw = to_fxbm(img)
                    is_real = True
                    if not preview_done:
                        log("ASCII-Vorschau (%s):\n%s" % (rel, ascii_preview(bw)))
                        preview_done = True
                except Exception as e:
                    data = None
        if data is None:
            data = fallback(series); fb += 1
        else:
            made += 1
        with open(outpath, "wb") as f: f.write(data)
        if is_real and series not in series_rep:
            series_rep[series] = data
        if i % 50 == 0:
            log(f"  {i}/{len(items)}  echt={made} fallback={fb}")
    # series icons
    sc = 0
    for series in sorted(set(p.split(os.sep)[0] for p in items)):
        sp = os.path.join(OUT, series, "_series.fxbm")
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "wb") as f:
            f.write(series_rep.get(series, fallback(series)))
        sc += 1
    log(f"FERTIG: episode-icons={len(items)} (echt={made}, fallback={fb}), serien-icons={sc}")

if __name__ == "__main__":
    main()
