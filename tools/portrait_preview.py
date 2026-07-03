#!/usr/bin/env python3
import os, json, hashlib, io
from PIL import Image, ImageOps, ImageChops, ImageDraw, ImageFont, ImageFilter
BASE="/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad"
CACHE=BASE+"/imgcache"; matches=json.load(open(BASE+"/matches.json"))
W,H=64,96
def cached(u):
    p=os.path.join(CACHE,hashlib.md5(u.encode()).hexdigest()); return p if os.path.exists(p) else None
def load_rgb(p):
    im=Image.open(p).convert("RGBA"); bg=Image.new("RGBA",im.size,(255,255,255,255)); return Image.alpha_composite(bg,im).convert("RGB")
def autocrop(rgb,thr=18):
    g=rgb.convert("L"); diff=ImageChops.difference(g,Image.new("L",g.size,255)); bb=diff.point(lambda p:255 if p>thr else 0).getbbox()
    if bb: x0,y0,x1,y1=bb; p=2; return rgb.crop((max(0,x0-p),max(0,y0-p),min(rgb.width,x1+p),min(rgb.height,y1+p)))
    return rgb
def atkinson(g):
    px=list(g.getdata()); w,h=g.size; a=[float(v) for v in px]
    for y in range(h):
        b=y*w
        for x in range(w):
            i=b+x; old=a[i]; new=255.0 if old>110 else 0.0; a[i]=new; e=(old-new)/8.0
            for dx,dy in ((1,0),(2,0),(-1,1),(0,1),(1,1),(0,2)):
                nx,ny=x+dx,y+dy
                if 0<=nx<w and 0<=ny<h: a[ny*w+nx]+=e
    o=Image.new("1",(w,h)); o.putdata([1 if v>127 else 0 for v in a]); return o
def icon(rgb):
    r=autocrop(rgb); im=r.copy(); im.thumbnail((W,H),Image.LANCZOS)
    c=Image.new("L",(W,H),255); c.paste(im.convert("L"),((W-im.width)//2,(H-im.height)//2))
    c=ImageOps.autocontrast(c,cutoff=3).filter(ImageFilter.UnsharpMask(1.2,120,2)); return atkinson(c)
def first(series):
    for rel,u in matches.items():
        if rel.startswith(series) and cached(u): return icon(load_rgb(cached(u)))
    return Image.new("1",(W,H),1)
names=["Bibi Blocksberg","Feuerwehrmann Sam","Benjamin Bluemchen","PAW Patrol","Disney","Yakari","Der kleine Drache Kokosnuss","Die Sendung mit der Maus"]
SC=5; pad=12; labh=18
# ganze 64x128 Screen-Mockups: Bild oben + Namezeile
def screen(ic,name):
    s=Image.new("1",(64,128),1); s.paste(ic,(0,0)); d=ImageDraw.Draw(s)
    d.line([0,97,63,97],fill=0); f=ImageFont.load_default()
    # Name grob umbrochen
    words=name.split(); line=""; y=101
    for w in words:
        if len(line)+len(w)+1>11: d.text((1,y),line,fill=0,font=f); y+=11; line=w
        else: line=(line+" "+w).strip()
    d.text((1,y),line,fill=0,font=f)
    return s
cols=4; rows=2
cw=64*SC+pad; ch=128*SC+pad+2
sheet=Image.new("L",(pad+cols*cw,labh+rows*ch),150); dd=ImageDraw.Draw(sheet)
try: bf=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",14)
except: bf=ImageFont.load_default()
dd.text((pad,2),"Hochformat 64x128  (Bild 64x96 + Name)",fill=0,font=bf)
for k,nm in enumerate(names):
    sc=screen(first(nm),nm); big=sc.convert("L").resize((64*SC,128*SC),Image.NEAREST)
    cx=k%cols; cy=k//cols; x=pad+cx*cw; y=labh+cy*ch
    sheet.paste(big,(x,y)); dd.rectangle([x-1,y-1,x+64*SC,y+128*SC],outline=0)
sheet.save(BASE+"/portrait_preview.png"); print("ok",sheet.size)
