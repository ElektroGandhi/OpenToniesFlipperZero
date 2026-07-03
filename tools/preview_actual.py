#!/usr/bin/env python3
# Dekodiert echte .fxbm und rendert das exakte App-Screen-Layout.
import os
from PIL import Image, ImageDraw, ImageFont
BASE="/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad"
F=BASE+"/icons"; S=BASE+"/icons_s"

def decode(path):
    d=open(path,"rb").read(); w,h=d[0],d[1]; bpr=(w+7)//8
    im=Image.new("1",(w,h),1)  # 1=weiss
    px=im.load()
    for y in range(h):
        for bxo in range(bpr):
            b=d[2+y*bpr+bxo]
            for bit in range(8):
                x=bxo*8+bit
                if x<w and (b>>bit)&1: px[x,y]=0  # schwarz
    return im

def screen_filmstrip(cpath, lpath, rpath, name, i, t):
    scr=Image.new("1",(128,64),1); d=ImageDraw.Draw(scr)
    try: l=decode(lpath); scr.paste(l,(2,12))
    except: pass
    try: r=decode(rpath); scr.paste(r,(94,12))
    except: pass
    try: c=decode(cpath); scr.paste(c,(36,0))
    except: pass
    d.rectangle([35,0,35+57,0+56],outline=0)
    f=ImageFont.load_default()
    nm=name[:20]
    d.text((1,56),nm,fill=0,font=f)
    d.text((104,56),f"{i}/{t}",fill=0,font=f)
    return scr

def sicon(series, root): return os.path.join(root, series, "_series.fxbm")

series=[("Bibi Blocksberg",3,255),("Feuerwehrmann Sam",8,255),("Der kleine Drache Kokosnuss",42,255),
        ("Benjamin Bluemchen",7,255),("Disney",90,255),("PAW Patrol",120,255)]
SC=7; pad=10; cols=2; rows=3
cw=128*SC+pad; ch=64*SC+pad+2
sheet=Image.new("L",(pad+cols*cw, pad+rows*ch),150); dd=ImageDraw.Draw(sheet)
for k,(name,i,t) in enumerate(series):
    cur=sicon(name,F); l=sicon(series[(k-1)%len(series)][0],S); r=sicon(series[(k+1)%len(series)][0],S)
    scr=screen_filmstrip(cur,l,r,name,i,t)
    big=scr.convert("L").resize((128*SC,64*SC),Image.NEAREST)
    cx=k%cols; cy=k//cols; x=pad+cx*cw; y=pad+cy*ch
    sheet.paste(big,(x,y)); dd.rectangle([x-1,y-1,x+128*SC,y+64*SC],outline=0)
sheet.save(BASE+"/preview_actual.png"); print("ok", sheet.size)
