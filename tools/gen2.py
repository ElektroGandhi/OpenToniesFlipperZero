#!/usr/bin/env python3
import os, json, hashlib, io, time, urllib.request
from PIL import Image, ImageOps, ImageChops, ImageDraw, ImageFont, ImageFilter

BASE = "/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad"
LOCAL = BASE + "/flipper-zero-tonies-master/German"
CACHE = BASE + "/imgcache"
MATCHES = BASE + "/matches.json"
LOG = BASE + "/gen2.log"
OUT_F = BASE + "/icons"     # Fokus 56
OUT_S = BASE + "/icons_s"   # Vorschau 32
FOC, PRV = 56, 32
UA = "Mozilla/5.0 (icon-fetch)"
os.makedirs(CACHE, exist_ok=True)
def log(m):
    with open(LOG, "a") as f: f.write(m + "\n")
    print(m, flush=True)
def fetch(url):
    cp = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest())
    if os.path.exists(cp):
        return open(cp, "rb").read()
    for a in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=15).read()
            open(cp, "wb").write(data); return data
        except Exception:
            time.sleep(0.3)
    return None
def autocrop(rgb, thr=18):
    g = rgb.convert("L"); diff = ImageChops.difference(g, Image.new("L", g.size, 255))
    bb = diff.point(lambda p: 255 if p > thr else 0).getbbox()
    if bb:
        x0,y0,x1,y1 = bb; p=2
        return rgb.crop((max(0,x0-p),max(0,y0-p),min(rgb.width,x1+p),min(rgb.height,y1+p)))
    return rgb
def atkinson(g):
    px=list(g.getdata()); w,h=g.size; a=[float(v) for v in px]
    for y in range(h):
        base=y*w
        for x in range(w):
            i=base+x; old=a[i]; new=255.0 if old>110 else 0.0; a[i]=new; e=(old-new)/8.0
            for dx,dy in ((1,0),(2,0),(-1,1),(0,1),(1,1),(0,2)):
                nx,ny=x+dx,y+dy
                if 0<=nx<w and 0<=ny<h: a[ny*w+nx]+=e
    o=Image.new("1",(w,h)); o.putdata([1 if v>127 else 0 for v in a]); return o
def pack(bw):  # bw: mode "1", 1=weiss/0=schwarz -> XBM LSB-first, gesetztes Bit = schwarz
    w,h=bw.size; px=bw.load(); bpr=(w+7)//8; out=bytearray([w,h])
    for y in range(h):
        for bxo in range(bpr):
            b=0
            for bit in range(8):
                x=bxo*8+bit
                if x<w and px[x,y]==0: b|=(1<<bit)
            out.append(b)
    return bytes(out)
def render(rgb,S):
    r=autocrop(rgb); im=r.copy(); im.thumbnail((S,S),Image.LANCZOS)
    c=Image.new("L",(S,S),255); c.paste(im.convert("L"),((S-im.width)//2,(S-im.height)//2))
    c=ImageOps.autocontrast(c,cutoff=3).filter(ImageFilter.UnsharpMask(1.2,120,2))
    return pack(atkinson(c))
def get_font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p,sz)
            except: pass
    return ImageFont.load_default()
def fallback(series,S):
    im=Image.new("L",(S,S),255); d=ImageDraw.Draw(im)
    d.rounded_rectangle([1,1,S-2,S-2],radius=6,outline=0,width=2)
    words=[w for w in series.replace("-"," ").split() if w]
    ini="".join(w[0] for w in words[:3]).upper() or series[:2].upper()
    f=get_font(int(S*0.5))
    try:
        bb=d.textbbox((0,0),ini,font=f); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
        d.text(((S-tw)//2-bb[0],(S-th)//2-bb[1]),ini,font=f,fill=0)
    except: d.text((3,S//3),ini,fill=0)
    return pack(im.convert("1"))
def load_rgb_bytes(raw):
    im=Image.open(io.BytesIO(raw)).convert("RGBA"); bg=Image.new("RGBA",im.size,(255,255,255,255))
    return Image.alpha_composite(bg,im).convert("RGB")

def main():
    open(LOG,"w").close()
    matches=json.load(open(MATCHES))
    items=[]
    for root,_,files in os.walk(LOCAL):
        for fn in files:
            if fn.endswith(".nfc"):
                items.append(os.path.relpath(os.path.join(root,fn),LOCAL))
    items.sort()
    log("items=%d"%len(items))
    real=fb=0
    rep_f={}; rep_s={}  # series -> repraesentatives Icon (Bytes)
    for i,rel in enumerate(items,1):
        series=rel.split(os.sep)[0]; base=rel[:-4]
        of=os.path.join(OUT_F,base+".fxbm"); os_=os.path.join(OUT_S,base+".fxbm")
        os.makedirs(os.path.dirname(of),exist_ok=True); os.makedirs(os.path.dirname(os_),exist_ok=True)
        url=matches.get(rel); df=ds=None
        if url:
            raw=fetch(url)
            if raw:
                try:
                    rgb=load_rgb_bytes(raw); df=render(rgb,FOC); ds=render(rgb,PRV); real+=1
                except Exception: df=None
        if df is None:
            df=fallback(series,FOC); ds=fallback(series,PRV); fb+=1
        else:
            if series not in rep_f: rep_f[series]=df; rep_s[series]=ds
        open(of,"wb").write(df); open(os_,"wb").write(ds)
        if i%50==0: log("  %d/%d real=%d fb=%d"%(i,len(items),real,fb))
    # Serien-Icons
    for series in sorted(set(p.split(os.sep)[0] for p in items)):
        for OUT,rep,S in ((OUT_F,rep_f,FOC),(OUT_S,rep_s,PRV)):
            sp=os.path.join(OUT,series,"_series.fxbm"); os.makedirs(os.path.dirname(sp),exist_ok=True)
            open(sp,"wb").write(rep.get(series, fallback(series,S)))
    log("FERTIG real=%d fb=%d"%(real,fb))
if __name__=="__main__": main()
