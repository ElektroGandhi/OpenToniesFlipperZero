#!/usr/bin/env python3
"""Rendert Figuren und Logo mit Chromium zu PNG."""
import glob, os, shutil, subprocess, sys, tempfile
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import figuren
MEDIA = os.path.dirname(HIER)
CHROME = os.environ.get("CHROME") or (sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"))) or [shutil.which("chromium")])[-1]


def foto(html, ziel, w, h, transparent=True):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "s.html")
        open(p, "w", encoding="utf-8").write(html)
        a = [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--user-data-dir={t}/p", f"--window-size={w},{h}", f"--screenshot={ziel}", "--virtual-time-budget=4000"]
        if transparent:
            a.append("--default-background-color=00000000")
        subprocess.run(a + ["file://" + p], check=True, capture_output=True, timeout=120)


def seite(svg, w, h):
    return f'<!doctype html><style>html,body{{margin:0;background:transparent}}svg{{display:block;width:{w}px;height:{h}px}}</style>{svg}'


if __name__ == "__main__":
    os.makedirs(os.path.join(MEDIA, "figuren"), exist_ok=True)
    for n, svg in figuren.ALLE.items():
        foto(seite(svg, 800, 800), os.path.join(MEDIA, "figuren", n + ".png"), 800, 800)
    foto(seite(figuren.LOGO, 1024, 1024), os.path.join(MEDIA, "logo.png"), 1024, 1024)
