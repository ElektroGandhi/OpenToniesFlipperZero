#!/usr/bin/env python3
# Hochformat-Icons 64x96 MIT KONTUR: Motiv-Maske -> schwarze Outline + kontrastierter Innenbereich.
import os, json, hashlib, io, time, urllib.request
from PIL import Image, ImageOps, ImageChops, ImageDraw, ImageFont, ImageFilter
HERE=os.path.dirname(os.path.abspath(__file__))
LOCAL=os.path.join(HERE,"tonies_repo"); CACHE=os.path.join(HERE,"imgcache")
LIBRARY=os.path.join(HERE,"..","web","library.json"); LOG=os.path.join(HERE,"gen4.log"); OUT=os.path.join(HERE,"icons_p")
W,H=64,96; UA="Mozilla/5.0 (icon-fetch)"
os.makedirs(CACHE,exist_ok=True)
def log(m):
    open(LOG,"a").write(m+"\n"); print(m,flush=True)
def fetch(url):
    cp=os.path.join(CACHE,hashlib.md5(url.encode()).hexdigest())
    if os.path.exists(cp): return open(cp,"rb").read()
    for a in range(2):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA}); data=urllib.request.urlopen(req,timeout=15).read(); open(cp,"wb").write(data); return data
        except Exception: time.sleep(0.3)
    return None
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
def pack(bw):
    w,h=bw.size; px=bw.load(); bpr=(w+7)//8; out=bytearray([w,h])
    for y in range(h):
        for bxo in range(bpr):
            b=0
            for bit in range(8):
                x=bxo*8+bit
                if x<w and px[x,y]==0: b|=(1<<bit)
            out.append(b)
    return bytes(out)
def fitL(rgb):
    r=autocrop(rgb); im=r.convert("L"); im.thumbnail((W,H),Image.LANCZOS)
    c=Image.new("L",(W,H),255); c.paste(im,((W-im.width)//2,(H-im.height)//2)); return c
def render_outline(rgb, thr=250):
    c=fitL(rgb)
    mask=c.point(lambda p:255 if p<thr else 0)
    mask=mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))  # open
    mask=mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))  # close
    interior=atkinson(ImageOps.autocontrast(c,cutoff=3))  # sanfter Innenbereich
    ring=ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(3)))  # 1px dezente Kontur auf der Kante
    pm=mask.load(); pr=ring.load(); pi=interior.load()
    out=Image.new("1",(W,H),1); po=out.load()
    for y in range(H):
        for x in range(W):
            if (pr[x,y]>127) or (pm[x,y]>127 and pi[x,y]==0): po[x,y]=0
    return out
def get_font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p,sz)
            except: pass
    return ImageFont.load_default()
def fallback(series):
    im=Image.new("L",(W,H),255); d=ImageDraw.Draw(im); d.rounded_rectangle([1,1,W-2,H-2],radius=6,outline=0,width=2)
    words=[w for w in series.replace("-"," ").split() if w]; ini="".join(w[0] for w in words[:3]).upper() or series[:2].upper()
    f=get_font(30)
    try:
        bb=d.textbbox((0,0),ini,font=f); tw=bb[2]-bb[0]; th=bb[3]-bb[1]; d.text(((W-tw)//2-bb[0],(H-th)//2-bb[1]),ini,font=f,fill=0)
    except: d.text((4,H//3),ini,fill=0)
    return pack(im.convert("1"))
def load_rgb_bytes(raw):
    im=Image.open(io.BytesIO(raw)).convert("RGBA"); bg=Image.new("RGBA",im.size,(255,255,255,255)); return Image.alpha_composite(bg,im).convert("RGB")
def bild_urls():
    # Die Bild-URLs stehen in der Bibliothek, die gen_library.py baut.
    return {e["path"]:e.get("img_url") for e in json.load(open(LIBRARY,encoding="utf-8"))["items"]}
def icon_fuer(rel,urls):
    url=urls.get(rel); raw=fetch(url) if url else None
    if raw:
        try: return pack(render_outline(load_rgb_bytes(raw))),True
        except Exception: pass
    return fallback(rel.split(os.sep)[-2] if os.sep in rel else rel),False
def schreibe(rel,data):
    of=os.path.join(OUT,rel[:-4]+".fxbm"); os.makedirs(os.path.dirname(of),exist_ok=True); open(of,"wb").write(data); return of
def main(nur=None):
    """Hochformat-Icons nach tools/icons_p/. `nur` = Liste relativer .nfc-Pfade; ohne = alle."""
    urls=bild_urls(); items=[]
    for root,_,files in os.walk(LOCAL):
        for fn in files:
            if fn.endswith(".nfc"): items.append(os.path.relpath(os.path.join(root,fn),LOCAL))
    if nur is not None: items=[r for r in items if r in set(nur)]
    items.sort(); log("items=%d"%len(items)); real=fb=0; rep={}
    for i,rel in enumerate(items,1):
        data,echt=icon_fuer(rel,urls); schreibe(rel,data); series=rel.split(os.sep)[0]
        if echt:
            real+=1; rep.setdefault(series,data)
        else: fb+=1
        if i%50==0: log("  %d/%d real=%d fb=%d"%(i,len(items),real,fb))
    for series in sorted({p.split(os.sep)[0] for p in items}):
        sp=os.path.join(OUT,series,"_series.fxbm"); os.makedirs(os.path.dirname(sp),exist_ok=True); open(sp,"wb").write(rep.get(series,fallback(series)))
    log("FERTIG real=%d fb=%d"%(real,fb)); return real,fb
if __name__=="__main__": main()
