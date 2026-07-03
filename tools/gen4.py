#!/usr/bin/env python3
# Hochformat-Icons 64x96 MIT KONTUR: Motiv-Maske -> schwarze Outline + kontrastierter Innenbereich.
import os, json, hashlib, io, time, urllib.request
from PIL import Image, ImageOps, ImageChops, ImageDraw, ImageFont, ImageFilter
BASE="/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad"
LOCAL=BASE+"/flipper-zero-tonies-master/German"; CACHE=BASE+"/imgcache"
MATCHES=BASE+"/matches.json"; LOG=BASE+"/gen4.log"; OUT=BASE+"/icons_p"
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
def main():
    open(LOG,"w").close(); matches=json.load(open(MATCHES))
    items=[]
    for root,_,files in os.walk(LOCAL):
        for fn in files:
            if fn.endswith(".nfc"): items.append(os.path.relpath(os.path.join(root,fn),LOCAL))
    items.sort(); log("items=%d"%len(items)); real=fb=0; rep={}
    for i,rel in enumerate(items,1):
        series=rel.split(os.sep)[0]; base=rel[:-4]; of=os.path.join(OUT,base+".fxbm"); os.makedirs(os.path.dirname(of),exist_ok=True)
        url=matches.get(rel); data=None
        if url:
            raw=fetch(url)
            if raw:
                try: data=pack(render_outline(load_rgb_bytes(raw))); real+=1
                except Exception: data=None
        if data is None: data=fallback(series); fb+=1
        else:
            if series not in rep: rep[series]=data
        open(of,"wb").write(data)
        if i%50==0: log("  %d/%d real=%d fb=%d"%(i,len(items),real,fb))
    for series in sorted(set(p.split(os.sep)[0] for p in items)):
        sp=os.path.join(OUT,series,"_series.fxbm"); os.makedirs(os.path.dirname(sp),exist_ok=True); open(sp,"wb").write(rep.get(series,fallback(series)))
    log("FERTIG real=%d fb=%d"%(real,fb))
if __name__=="__main__": main()
