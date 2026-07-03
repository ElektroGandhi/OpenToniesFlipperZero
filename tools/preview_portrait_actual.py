#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
BASE="/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad"
P=BASE+"/icons_p"
def decode(path):
    d=open(path,"rb").read(); w,h=d[0],d[1]; bpr=(w+7)//8
    im=Image.new("1",(w,h),1); px=im.load()
    for y in range(h):
        for bxo in range(bpr):
            b=d[2+y*bpr+bxo]
            for bit in range(8):
                x=bxo*8+bit
                if x<w and (b>>bit)&1: px[x,y]=0
    return im
def wrap(d,x,y,w,s,f,maxl=2):
    words=s.split(); line=""; ln=0
    for wd in words:
        if len(line)+len(wd)+1>12:
            d.text((x,y+ln*10),line,fill=0,font=f); ln+=1; line=wd
            if ln>=maxl: return
        else: line=(line+" "+wd).strip()
    if ln<maxl: d.text((x,y+ln*10),line,fill=0,font=f)
def screen(iconpath,name,i,t,play=False):
    s=Image.new("1",(64,128),1); d=ImageDraw.Draw(s); f=ImageFont.load_default()
    try:
        ic=decode(iconpath); s.paste(ic,((64-ic.width)//2,0))
    except: pass
    if play:
        d.text((16,104),"Spielt!",fill=0,font=f); d.text((2,118),"Zurueck=Stop",fill=0,font=f)
    else:
        d.line([0,98,63,98],fill=0); wrap(d,1,101,62,name,f,2)
        d.text((1,119),f"{i}/{t}",fill=0,font=f)
    return s
def sic(series): return os.path.join(P,series,"_series.fxbm")
series=["Bibi Blocksberg","Feuerwehrmann Sam","Benjamin Bluemchen","PAW Patrol",
        "Disney","Yakari","Der kleine Drache Kokosnuss","Die Sendung mit der Maus & dem Elefanten"]
SC=5; pad=12; cols=4; rows=2
cw=64*SC+pad; ch=128*SC+pad
sheet=Image.new("L",(pad+cols*cw,pad+rows*ch),150); dd=ImageDraw.Draw(sheet)
for k,nm in enumerate(series):
    sc=screen(sic(nm),nm,k+1,255)
    big=sc.convert("L").resize((64*SC,128*SC),Image.NEAREST)
    x=pad+(k%cols)*cw; y=pad+(k//cols)*ch
    sheet.paste(big,(x,y)); dd.rectangle([x-1,y-1,x+64*SC,y+128*SC],outline=0)
sheet.save(BASE+"/preview_portrait_actual.png"); print("ok",sheet.size)
