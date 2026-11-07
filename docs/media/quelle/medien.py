#!/usr/bin/env python3
"""Banner, Bildschirmfotos, GIF und Video aus echten Geräte-Bildschirmen bauen.

    python3 docs/media/quelle/medien.py <web-demo-url>

Die Adresse soll eine Kopie der Web-Demo ohne den Browser-Hinweis zeigen: Headless-Chromium
hat kein Bluetooth und würde ihn sonst mitfotografieren.

Eingang: docs/media/quelle/frames/*.png (per tools/flipper_rpc.py aufgenommen, Demo-Bibliothek).
"""
import base64, json, os, subprocess, sys, tempfile
from PIL import Image

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import rendern

MEDIA = os.path.dirname(HIER)
WURZEL = os.path.dirname(os.path.dirname(MEDIA))
FRAMES = os.path.join(HIER, "frames")
FONT = os.path.join(WURZEL, "web", "font")
LCD_HELL, LCD_DUNKEL = (255, 138, 28), (43, 26, 12)


def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()


def lcd(name, zoom=4):
    """Bildschirm in LCD-Farben, ohne Glättung vergrößert."""
    i = Image.open(os.path.join(FRAMES, name + ".png")).convert("L")
    i = i.resize((64, 128), Image.NEAREST).point(lambda p: 255 if p > 127 else 0)
    bunt = Image.merge("RGB", [i.point(lambda p: LCD_HELL[k] if p else LCD_DUNKEL[k]) for k in range(3)])
    return bunt.resize((64 * zoom, 128 * zoom), Image.NEAREST)


def datenuri_lcd(name):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t:
        lcd(name, 8).save(t.name)
    s = "data:image/png;base64," + b64(t.name)
    os.unlink(t.name)
    return s


CSS = f"""
@font-face{{font-family:B;src:url(data:font/woff2;base64,{b64(os.path.join(FONT, 'Baloo2-800.woff2'))});font-weight:800}}
@font-face{{font-family:N;src:url(data:font/woff2;base64,{b64(os.path.join(FONT, 'Nunito-800.woff2'))});font-weight:800}}
@font-face{{font-family:N;src:url(data:font/woff2;base64,{b64(os.path.join(FONT, 'Nunito-400.woff2'))});font-weight:400}}
*{{box-sizing:border-box}}html,body{{margin:0}}
.grund{{width:1280px;height:720px;position:relative;overflow:hidden;font-family:N,sans-serif;color:#2b2140;
background:radial-gradient(900px 620px at 88% 12%,#ffe9c9 0,transparent 70%),linear-gradient(135deg,#fff8ee,#ffd9b0)}}
.geraet{{position:absolute;background:#fbf7f1;border-radius:44px;padding:26px 24px 62px;
box-shadow:0 26px 60px rgba(90,50,10,.32),inset 0 -5px 0 rgba(0,0,0,.08)}}
.geraet img{{display:block;image-rendering:pixelated;border-radius:6px;border:5px solid #2b2140}}
.geraet:after{{content:"";position:absolute;left:50%;bottom:16px;width:30px;height:30px;margin-left:-15px;border-radius:50%;background:#ff8a1c;box-shadow:0 2px 0 rgba(0,0,0,.25)}}
h1{{font:800 96px/1 B,sans-serif;margin:0;letter-spacing:-.01em}}
.de{{font:800 56px/1.12 B,sans-serif;margin:0}}.en{{font:400 30px/1.25 N,sans-serif;margin:14px 0 0;color:#5a4a68}}
.klein{{font:400 22px/1.3 N,sans-serif;color:#5a4a68}}
.fig{{position:absolute;filter:drop-shadow(0 12px 12px rgba(90,50,10,.22))}}
"""


def figur(n):
    return "data:image/png;base64," + b64(os.path.join(MEDIA, "figuren", n + ".png"))


def geraet(bild, x, y, breite=256):
    return f'<div class="geraet" style="left:{x}px;top:{y}px"><img src="{bild}" width="{breite}"></div>'


def seite(inhalt, h=720):
    return f'<!doctype html><meta charset=utf-8><style>{CSS}</style><div class="grund" style="height:{h}px">{inhalt}</div>'


def banner():
    figs = "".join(f'<img class="fig" src="{figur(n)}" width="{w}" style="left:{x}px;top:{y}px">'
                   for n, w, x, y in [("fuchs", 190, 90, 408), ("eule", 170, 270, 428), ("drache", 170, 430, 428), ("igel", 150, 590, 448)])
    return seite(f'''<div style="position:absolute;left:84px;top:76px;width:780px">
      <div style="display:flex;align-items:center;gap:26px"><img src="data:image/png;base64,{b64(os.path.join(MEDIA, 'logo.png'))}" width="112"><h1>OpenTonies</h1></div>
      <p class="de" style="font-size:42px;margin-top:26px">Figur aussuchen, auf die Box legen, zuhören.</p>
      <p class="en" style="font-size:25px;margin-top:10px">Pick a figure, put it on the box, listen. Kid-friendly app for Flipper Zero.</p></div>
      {figs}{geraet(datenuri_lcd('serie_1'), 894, 24, 256).replace('width="256"', 'width="244"')}''', 640)


def folie(bild, de, en):
    return seite(f'''{geraet(datenuri_lcd(bild), 136, 30, 280).replace('width="280"', 'width="266"')}
      <div style="position:absolute;left:560px;top:230px;width:640px"><p class="de">{de}</p><p class="en">{en}</p></div>
      <p class="klein" style="position:absolute;right:42px;bottom:24px;margin:0">aufgenommen am echten Gerät · recorded on the real device</p>''')


FOLIEN = [
    ("serie_1", 1.0, "Figur am Bild aussuchen", "Pick a figure by its picture"),
    ("serie_2", 0.8, "Figur am Bild aussuchen", "Pick a figure by its picture"),
    ("serie_3", 0.8, "Figur am Bild aussuchen", "Pick a figure by its picture"),
    ("serie_4", 0.8, "Figur am Bild aussuchen", "Pick a figure by its picture"),
    ("serie_5", 0.9, "Figur am Bild aussuchen", "Pick a figure by its picture"),
    ("serie_5_favorit", 2.2, "Langes OK merkt sich den Favoriten", "A long press on OK saves a favorite"),
    ("folge_1", 1.5, "Serie öffnen, Folge wählen", "Open a series, choose an episode"),
    ("folge_2", 1.5, "Serie öffnen, Folge wählen", "Open a series, choose an episode"),
    ("spielt", 3.2, "Auf die Box legen und zuhören", "Put it on the box and listen"),
    ("setup_timer", 2.4, "Der Auto-Timer spart Strom", "The auto-timer saves power"),
    ("setup_puffer", 2.8, "Neu: 5 Minuten Puffer", "New: a 5-minute buffer"),
    ("setup_puffer_10", 2.0, "Einstellbar von 0 bis 30 Minuten", "Adjustable from 0 to 30 minutes"),
]


def gif():
    seq = [("serie_1", 1000), ("serie_2", 600), ("serie_3", 600), ("serie_4", 600), ("serie_5", 700), ("serie_5_favorit", 1300),
           ("serie_1b", 600), ("folge_1", 1100), ("folge_2", 1100), ("spielt", 1900), ("setup_timer", 1200),
           ("setup_puffer", 1700), ("setup_puffer_10", 1200), ("setup_puffer_5", 1200)]
    bilder = []
    for name, _ in seq:
        i = lcd(name, 3)
        rahmen = Image.new("RGB", (i.width + 28, i.height + 28), (43, 33, 64))
        rahmen.paste(i, (14, 14))
        bilder.append(rahmen.quantize(8, dither=Image.Dither.NONE))
    bilder[0].save(os.path.join(MEDIA, "demo.gif"), save_all=True, append_images=bilder[1:],
                   duration=[d for _, d in seq], loop=0, optimize=True)


def screens():
    namen = ["serie_5_favorit", "folge_2", "spielt", "setup_puffer"]
    z = [lcd(n, 3) for n in namen]
    r = 12
    bild = Image.new("RGB", (sum(i.width + 2 * r for i in z) + r * 3, z[0].height + 2 * r), (255, 255, 255))
    x = 0
    for i in z:
        k = Image.new("RGB", (i.width + 2 * r, i.height + 2 * r), (43, 33, 64))
        k.paste(i, (r, r))
        bild.paste(k, (x, 0))
        x += k.width + r
    bild.save(os.path.join(MEDIA, "screens.png"), optimize=True)


def web(url, ziel):
    t = tempfile.mkdtemp()
    p = os.path.join(t, "w.png")
    subprocess.run([rendern.CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--user-data-dir={t}/p", "--window-size=375,760", "--force-device-scale-factor=2",
                    "--enable-experimental-web-platform-features", "--enable-features=WebBluetooth",
                    "--virtual-time-budget=6000", f"--screenshot={p}", url], check=True, capture_output=True, timeout=90)
    i = Image.open(p).convert("RGB")
    rand = 26
    k = Image.new("RGBA", (i.width + 2 * rand, i.height + 2 * rand), (0, 0, 0, 0))
    from PIL import ImageDraw
    m = Image.new("L", k.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, k.width - 1, k.height - 1), 90, fill=255)
    k.paste((43, 33, 64, 255), (0, 0), m)
    m2 = Image.new("L", i.size, 0)
    ImageDraw.Draw(m2).rounded_rectangle((0, 0, i.width - 1, i.height - 1), 66, fill=255)
    k.paste(i, (rand, rand), m2)
    k.thumbnail((640, 1400))
    k.save(ziel, optimize=True)


def video(webbild):
    t = tempfile.mkdtemp()
    liste = []
    def rendern_folie(html, dauer):
        p = os.path.join(t, f"s{len(liste):02d}.png")
        rendern.foto(html, p, 1280, 720, transparent=False)
        liste.append((p, dauer))

    rendern_folie(banner().replace("height:640px", "height:720px;padding-top:40px"), 3.5)
    for name, d, de, en in FOLIEN:
        rendern_folie(folie(name, de, en), d)
    w = "data:image/png;base64," + b64(webbild)
    figs = "".join(f'<img class="fig" src="{figur(n)}" width="150" style="left:{x}px;top:{y}px">'
                   for n, x, y in [("robo", 720, 440), ("drache", 900, 440), ("eule", 1080, 440)])
    rendern_folie(seite(f'''<img src="{w}" height="680" style="position:absolute;left:150px;top:20px">
      <div style="position:absolute;left:560px;top:140px;width:660px"><p class="de">Bibliothek fürs Telefon (Beta)</p>
      <p class="en">A library for your phone (beta). We are still working on it, Bluetooth is not yet tested on real hardware.</p></div>{figs}'''), 4.5)
    rendern_folie(seite(f'''<div style="text-align:center;padding-top:150px">
      <img src="data:image/png;base64,{b64(os.path.join(MEDIA, 'logo.png'))}" width="170"><h1 style="margin-top:20px">OpenTonies</h1>
      <p class="en">Open Source · MIT · Deutsch &amp; English</p>
      <p class="en" style="font-weight:800">github.com/ElektroGandhi/OpenToniesFlipperZero</p>
      <p class="klein">Ideas by BLOTTO · vibed by OPUS · Musik: eigene Synthese / own synthesis</p></div>'''), 4.0)
    konkat = os.path.join(t, "liste.txt")
    with open(konkat, "w") as f:
        for p, d in liste:
            f.write(f"file '{p}'\nduration {d}\n")
        f.write(f"file '{liste[-1][0]}'\n")
    gesamt = sum(d for _, d in liste)
    wav = os.path.join(t, "m.wav")
    subprocess.run([sys.executable, os.path.join(HIER, "musik.py"), wav, str(gesamt)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", konkat, "-i", wav,
                    "-vf", f"fps=30,format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st={gesamt - 0.8}:d=0.8",
                    "-c:v", "libx264", "-crf", "24", "-preset", "slow", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", "-shortest", os.path.join(MEDIA, "demo.mp4")], check=True)
    return gesamt


if __name__ == "__main__":
    url = sys.argv[1]
    rendern.foto(banner(), os.path.join(MEDIA, "banner.png"), 1280, 640, transparent=False)
    screens()
    gif()
    web(url, os.path.join(MEDIA, "web.png"))
    print("Video:", video(os.path.join(MEDIA, "web.png")), "s")
    for n in ("banner.png", "screens.png", "demo.gif", "web.png", "demo.mp4"):
        print(n, os.path.getsize(os.path.join(MEDIA, n)) // 1024, "kB")
