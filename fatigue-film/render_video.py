"""Deterministic science-animation renderer: Pillow frames + FFmpeg H.264.

Usage: python render_video.py --preview
       python render_video.py --render --workers 3
The included audio/captions make the video reproducible offline.
"""
import argparse
import bisect
import concurrent.futures
import functools
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'storyboard.json').read_text())
SCENES=DATA['scenes']
W,H=DATA['resolution']; FPS=DATA['fps']
OUT=ROOT/'output'; OUT.mkdir(exist_ok=True)
TMP=ROOT/'build'; TMP.mkdir(exist_ok=True)
BG='#091321'; PANEL='#102338'; EDGE='#294258'; WHITE='#edf6ff'
MUTED='#a1b5c9'; CYAN='#40dcdf'; BLUE='#6c9fff'; GOLD='#ffc36b'; RED='#ff737d'


@functools.lru_cache(None)
def font(size=32,bold=False,mono=False):
    name='DejaVuSansMono.ttf' if mono else ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    return ImageFont.truetype(str(ROOT/'assets'/'fonts'/name),int(size))


def tw(text,size=32,bold=False):
    return font(size,bold).getlength(text)


def text(d,xy,s,size=32,color=WHITE,bold=False,anchor=None):
    d.text(xy,s,font=font(size,bold),fill=color,anchor=anchor,stroke_width=0)


def lines(d,xy,s,width,size=32,color=WHITE,bold=False,spacing=1.32):
    x,y=xy; yy=y
    for para in s.split('\n'):
        row=''
        for word in para.split():
            nxt=(row+' '+word).strip()
            if tw(nxt,size,bold)>width and row:
                text(d,(x,yy),row,size,color,bold); yy+=size*spacing; row=word
            else: row=nxt
        text(d,(x,yy),row,size,color,bold); yy+=size*spacing
    return yy


def fittext(d,xy,s,maxwidth,size=60,color=WHITE,bold=True):
    while tw(s,size,bold)>maxwidth: size-=1
    text(d,xy,s,size,color,bold)


def panel(d,box,fill=PANEL,outline=EDGE,r=24):
    d.rounded_rectangle(tuple(map(int,box)),r,fill=fill,outline=outline,width=2)


def line(d,pts,color=CYAN,width=5):
    d.line([(int(x),int(y)) for x,y in pts],fill=color,width=int(width),joint='curve')


def arrow(d,a,b,color=CYAN,width=7,head=20):
    line(d,[a,b],color,width)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    p1=(b[0]-head*math.cos(ang)+head*.55*math.sin(ang),b[1]-head*math.sin(ang)-head*.55*math.cos(ang))
    p2=(b[0]-head*math.cos(ang)-head*.55*math.sin(ang),b[1]-head*math.sin(ang)+head*.55*math.cos(ang))
    d.polygon([b,p1,p2],fill=color)


def dashed(d,a,b,color=MUTED,width=3,dash=12):
    dist=math.dist(a,b)
    for n in np.arange(0,dist,dash*1.8):
        p=n/dist; q=min((n+dash)/dist,1)
        line(d,[(a[0]+p*(b[0]-a[0]),a[1]+p*(b[1]-a[1])),
                (a[0]+q*(b[0]-a[0]),a[1]+q*(b[1]-a[1]))],color,width)


def dot(d,x,y,r=8,c=CYAN):
    d.ellipse((x-r,y-r,x+r,y+r),fill=c)


def ring(d,x,y,r=30,c=CYAN,width=4):
    d.ellipse((x-r,y-r,x+r,y+r),outline=c,width=width)


def chip(d,x,y,label,color=CYAN,size=26):
    width=tw(label,size,True)+36
    panel(d,(x,y,x+width,y+size+26),fill='#142b40',outline=color,r=14)
    text(d,(x+18,y+10),label,size,color,True)
    return width


def clamp(x): return max(0.,min(1.,x))
def smooth(x): x=clamp(x); return x*x*(3-2*x)


@functools.lru_cache(None)
def background():
    yy,xx=np.mgrid[0:H,0:W]
    glow=np.exp(-(((xx-W*.8)/(W*.6))**2+((yy-H*.25)/(H*.8))**2)*3)
    arr=np.empty((H,W,3),dtype=np.uint8)
    for i,(a,b) in enumerate([(7,7),(16,17),(29,24)]): arr[:,:,i]=a+b*glow
    im=Image.fromarray(arr); d=ImageDraw.Draw(im)
    for x in range(0,W,80): line(d,[(x,0),(x,H)],'#122336',1)
    for y in range(0,H,80): line(d,[(0,y),(W,y)],'#122336',1)
    return im


@functools.lru_cache(None)
def photo(name): return Image.open(ROOT/'assets'/name).convert('RGB')


@functools.lru_cache(None)
def sized_photo(name,w,h):
    src=photo(name); out=src.copy(); out.thumbnail((int(w),int(h)),Image.Resampling.LANCZOS)
    return out


def place(im,name,box):
    x,y,x2,y2=box; pic=sized_photo(name,x2-x,y2-y)
    px=int(x+(x2-x-pic.width)/2); py=int(y+(y2-y-pic.height)/2)
    im.paste(pic,(px,py)); return px,py,pic.width,pic.height


@functools.lru_cache(None)
def formula_img(expr,size=72,color=WHITE):
    import matplotlib
    from matplotlib.mathtext import math_to_image
    from matplotlib.font_manager import FontProperties
    import io
    buf=io.BytesIO()
    with matplotlib.rc_context({'savefig.transparent':True,'savefig.facecolor':'none','figure.facecolor':'none'}):
        math_to_image('$'+expr+'$',buf,prop=FontProperties(size=size),dpi=100,color=color,format='png')
    buf.seek(0); return Image.open(buf).convert('RGBA')


def formula(im,expr,x,y,size=72,color=WHITE):
    p=formula_img(expr,size,color); im.alpha_composite(p,(int(x),int(y)))
    return p.width,p.height


def base(scene,t):
    im=background().convert('RGBA'); d=ImageDraw.Draw(im)
    case=t>=135; accent=GOLD if case else CYAN
    text(d,(80,44),'02  /  BICYCLE APPLICATION' if case else '01  /  THE SCIENCE',25,accent,True)
    text(d,(1840,46),f'{int(t)//60:02}:{int(t)%60:02}  /  03:00',24,MUTED,anchor='ra')
    if scene['id']!='intro': fittext(d,(80,100),scene['title'],1760,60)
    line(d,[(80,1047),(1840,1047)],EDGE,6)
    line(d,[(80,1047),(80+1760*min(t,135)/180,1047)],CYAN,6)
    if t>135: line(d,[(80+1320,1047),(80+1760*t/180,1047)],GOLD,6)
    line(d,[(1400,1037),(1400,1057)],WHITE,2)
    return im,d


def caption(im,t):
    d=ImageDraw.Draw(im)
    caps=get_captions(); starts=[c['start'] for c in caps]
    idx=bisect.bisect_right(starts,t)-1
    if idx>=0 and t<=caps[idx]['end']:
        s=caps[idx]['text']; row=''; rows=[]; size=42
        for word in s.split():
            test=(row+' '+word).strip()
            if tw(test,size)>1700 and row: rows.append(row); row=word
            else: row=test
        if row: rows.append(row)
        assert len(rows)<=2, (t,s,rows)
        panel(d,(70,924,1850,1030),fill='#030911',outline='#293d51',r=18)
        y=929 if len(rows)==2 else 953
        for row in rows:
            text(d,(960,y),row,size,WHITE,anchor='ma'); y+=48


@functools.lru_cache(None)
def get_captions(): return json.loads((ROOT/'captions.json').read_text())


def bike(d,ox,oy,s=1.,phase=0,highlight=True,force=False):
    # Coordinates describe a physically recognizable diamond frame.
    def p(x,y): return ox+x*s,oy+y*s
    def seg(coords,c,w): line(d,[p(*x) for x in coords],c,max(1,int(w*s)))
    rear=(130,360); front=(740,360); bb=(405,350); seat=(320,120); head=(615,120)
    for c in (rear,front):
        x,y=p(*c); r=155*s
        ring(d,x,y,r,'#657e97',max(3,int(11*s)))
        ring(d,x,y,r-13*s,'#233c51',max(2,int(4*s)))
        for a in range(0,360,30):
            ang=math.radians(a)+phase*.25
            seg([c,(c[0]+146*math.cos(ang),c[1]+146*math.sin(ang))],'#365066',2)
        dot(d,x,y,10*s,MUTED)
    for pts in [[rear,seat,bb,rear],[seat,head,bb],[head,front]]: seg(pts,CYAN,13)
    seg([(615,120),(590,63),(650,63),(666,87)],MUTED,10)
    seg([(320,120),(307,69)],MUTED,10)
    seg([(265,68),(350,68)],WHITE,13)
    seg([(130,339),(405,313)],MUTED,4); seg([(130,381),(405,389)],MUTED,4)
    x,y=p(*bb); ring(d,x,y,48*s,GOLD,int(6*s)); ring(d,x,y,35*s,'#8a6b40',int(3*s))
    pedal=(bb[0]+94*math.cos(phase),bb[1]+94*math.sin(phase))
    back=(bb[0]-94*math.cos(phase),bb[1]-94*math.sin(phase))
    seg([back,bb],'#57718a',9); seg([bb,pedal],GOLD,16)
    seg([(pedal[0]-30,pedal[1]),(pedal[0]+30,pedal[1])],WHITE,11)
    seg([(back[0]-25,back[1]),(back[0]+25,back[1])],MUTED,9)
    if highlight: ring(d,x,y,122*s,GOLD,3)
    if force:
        px,py=p(*pedal); length=(60+70*(1+math.cos(phase))*.5)*s
        arrow(d,(px,py-length-24*s),(px,py-20*s),RED,max(3,int(7*s)),20*s)
    return p(*bb),p(*pedal)


def plate(d,box,a=.3,load=1.,broken=False,gap=0.,labels=False):
    x,y,x2,y2=box; w=x2-x; h=y2-y; mid=(y+y2)/2
    tip=x+w*a
    if not broken:
        panel(d,box,fill='#627d93',outline='#b0c5d4',r=12)
        # Edge notch and a through-thickness crack, viewed from the face.
        d.polygon([(x,mid-14),(x+28,mid),(x,mid+14)],fill=BG)
        pts=[(x+22,mid)]
        for j in range(1,31):
            px=x+22+(tip-x-22)*j/30
            py=mid+math.sin(j*2.1)*h*.014
            pts.append((px,py))
        line(d,pts,'#07111d',7)
        line(d,pts,RED,3)
        dot(d,tip,mid,6,RED)
    else:
        cut=[(x+w*j/20,mid+math.sin(j*2.4)*h*.033) for j in range(21)]
        d.polygon([(x,y-gap),(x2,y-gap)]+[(px,py-gap) for px,py in reversed(cut)],fill='#627d93',outline='#b0c5d4')
        d.polygon([(px,py+gap) for px,py in cut]+[(x2,y2+gap),(x,y2+gap)],fill='#627d93',outline='#b0c5d4')
        line(d,[(px,py-gap) for px,py in cut],RED,4)
        line(d,[(px,py+gap) for px,py in cut],RED,4)
    for px in (x+w*.3,x+w*.7):
        L=(35+load*36)
        arrow(d,(px,y-gap-12),(px,y-gap-12-L),CYAN,6,16)
        arrow(d,(px,y2+gap+12),(px,y2+gap+12+L),CYAN,6,16)
    if labels and not broken:
        yy=y2+112
        line(d,[(tip,yy-10),(tip,yy+10)],GOLD,3)
        line(d,[(x2,yy-10),(x2,yy+10)],GOLD,3)
        line(d,[(tip,yy),(x2,yy)],GOLD,3)
        text(d,((tip+x2)/2,yy+17),'Intact metal',28,GOLD,anchor='ma')
    return tip,mid


def sn_chart(d,box=(180,290,1340,770),scatter=False,labels=True,curve_color=CYAN):
    x,y,x2,y2=box
    def pt(logn,S): return x+(logn-3)/4*(x2-x),y2-(S-80)/320*(y2-y)
    for S in [100,200,300,400]:
        yy=pt(3,S)[1]; line(d,[(x,yy),(x2,yy)],'#253c50',2)
        if labels: text(d,(x-22,yy),str(S),26,MUTED,anchor='rm')
    for i,lab in enumerate(['10³','10⁴','10⁵','10⁶','10⁷']):
        xx=pt(i+3,80)[0]; line(d,[(xx,y),(xx,y2)],'#253c50',2)
        if labels: text(d,(xx,y2+20),lab,30,MUTED,anchor='ma')
    arrow(d,(x,y2),(x,y-18),MUTED,3,12); arrow(d,(x,y2),(x2+20,y2),MUTED,3,12)
    pts=[pt(z,540-60*z) for z in np.linspace(3,7,100)]
    line(d,pts,curve_color,6)
    if scatter:
        for k,(z,shift) in enumerate([(3.2,-18),(3.55,12),(3.9,-9),(4.15,20),(4.42,-22),(4.8,14),(5.1,-11),(5.4,19),(5.7,-16),(6.05,13),(6.35,-9),(6.7,9)]):
            px,py=pt(z,540-60*z+shift); ring(d,px,py,8,BLUE,3)
    return pt


def reading(d,pt,logn,S,phase,color,labelbox=None):
    origin=pt(3,S); hit=pt(logn,S); end=pt(logn,80)
    f=smooth(phase/.44); g=smooth((phase-.44)/.44)
    if f>0:
        arrow(d,origin,(origin[0]+(hit[0]-origin[0])*f,hit[1]),color,5,14)
    if g>0: arrow(d,hit,(hit[0],hit[1]+(end[1]-hit[1])*g),color,5,14)
    if phase>=.44: dot(d,*hit,10,color)


def intro(im,d,u):
    text(d,(80,124),'FATIGUE FAILURE',88,WHITE,True)
    text(d,(84,239),'From Small Cracks',54,CYAN,True)
    text(d,(84,307),'to Sudden Fracture',54,CYAN,True)
    panel(d,(80,416,1055,883))
    chip(d,108,444,'FIRST  02:15',CYAN)
    text(d,(345,448),'Understand the science',34,WHITE,True)
    items=['Repeated loading, even below yield strength',
           'Crack initiation → growth → final fracture',
           'S-N curves: amplitude, life and scatter',
           'Stress intensity and fracture toughness']
    for i,s in enumerate(items):
        dot(d,125,528+i*58,5,CYAN); text(d,(150,508+i*58),s,29,MUTED)
    line(d,[(108,751),(1025,751)],EDGE,2)
    chip(d,108,779,'THEN  00:45',GOLD)
    text(d,(345,786),'Apply it to a bicycle crank',30,WHITE,True)
    bike(d,1090,345,.78,phase=.75+u*.12,highlight=True)
    text(d,(1450,820),'THE BICYCLE CASE',24,GOLD,True,anchor='ma')


def loading(im,d,u):
    panel(d,(80,224,1040,872)); panel(d,(1070,224,1840,872))
    text(d,(110,248),'Nominal stress over time',32,WHITE,True)
    x,y,x2,y2=145,365,995,695
    dashed(d,(x,370),(x2,370),RED,3)
    text(d,(x+15,326),'Yield strength',28,RED)
    line(d,[(x,735),(x2,735)],MUTED,3)
    xx=np.linspace(x,x2,350)
    pts=[(px,540-105*math.sin((px-x)/(x2-x)*6*math.pi-u*2.5)) for px in xx]
    line(d,pts,CYAN,6)
    text(d,(570,760),'Repeated cycles',30,MUTED,anchor='ma')
    chip(d,120,808,'Peak stress stays below yield',CYAN,25)
    plate(d,(1190,420,1725,646),.15,load=.6+.5*math.sin(u*3))
    text(d,(1450,270),'ONE LOAD ≠ MANY LOADS',30,GOLD,True,anchor='ma')
    text(d,(1455,782),'Damage can accumulate',32,WHITE,True,anchor='ma')


def specimen(im,d,u):
    chip(d,80,210,'REAL SPECIMEN  /  SEM PHOTOGRAPH',CYAN,25)
    panel(d,(80,288,1840,835),fill='#03070b')
    place(im,'nist_specimen.png',(100,305,1820,817))
    d=ImageDraw.Draw(im)
    text(d,(95,849),'White arrow: initiation at a lack-of-fusion defect',29,GOLD,True)
    text(d,(1825,851),'NIST  |  Ti-6Al-4V titanium alloy',25,MUTED,anchor='ra')
    text(d,(95,890),'Source: nist.gov/image/semti-6al-4vpng-0  •  Photo resized; original arrows and scale bars retained.',22,MUTED)


def growth(im,d,u):
    stages=['1  CRACK STARTS','2  CRACK GROWS','3  FAST FRACTURE']
    active=0 if u<3.1 else (1 if u<11.4 else 2)
    for i,label in enumerate(stages):
        x=80+i*596; panel(d,(x,218,x+568,295),outline=(CYAN if i==active else EDGE))
        text(d,(x+284,239),label,30,CYAN if i==active else MUTED,True,anchor='ma')
    if u<3.1: a=.04+.07*smooth(u/3.1)
    else: a=.11+.65*smooth((u-3.1)/8.3)
    broken=u>=11.4; gap=25*smooth((u-11.4)/.35)
    plate(d,(370,436,1520,674),a,load=.65+.4*math.sin(u*5),broken=broken,gap=gap,labels=True)
    if not broken:
        text(d,(92,454),'Local stress',29,GOLD,True); text(d,(92,493),'concentration',29,GOLD,True)
        arrow(d,(265,526),(382,555),GOLD,4,14)
    else:
        text(d,(960,787),'The remaining section can no longer carry the load.',35,RED,True,anchor='ma')
    text(d,(80,878),'SCHEMATIC  •  Damage accumulates over cycles; growth is not shown at a real-time rate.',24,MUTED)


def sn_axes(im,d,u):
    text(d,(115,213),'Stress amplitude, S (MPa)',31,CYAN,True)
    sn_chart(d)
    text(d,(770,834),'Cycles to failure, N  (log scale)',31,CYAN,True,anchor='ma')
    panel(d,(1400,240,1840,806))
    text(d,(1430,275),'AMPLITUDE',25,GOLD,True)
    formula(im,r'S=\frac{\sigma_{max}-\sigma_{min}}{2}',1435,335,38)
    text(d,(1430,456),'Half the stress range',26,MUTED)
    text(d,(1430,548),'LOG SCALE',25,CYAN,True)
    text(d,(1430,601),'10,000 → 100,000',28,WHITE,True)
    text(d,(1430,650),'Each step is ×10',28,MUTED)
    text(d,(85,886),'ILLUSTRATIVE DATA  •  Not measured bicycle-crank results.',24,GOLD)


def sn_read(im,d,u):
    text(d,(115,213),'Stress amplitude, S (MPa)',31,CYAN,True)
    pt=sn_chart(d)
    reading(d,pt,4,300,clamp(u/5.9),RED)
    if u>5.5: reading(d,pt,6,180,clamp((u-5.5)/3.7),GOLD)
    text(d,(770,834),'Cycles to failure, N  (log scale)',31,CYAN,True,anchor='ma')
    panel(d,(1400,240,1840,806))
    text(d,(1430,280),'HIGHER AMPLITUDE',25,RED,True)
    text(d,(1430,335),'300 MPa',47,WHITE,True)
    if u>4: text(d,(1430,397),'→ 10,000 cycles',29,RED,True)
    text(d,(1430,523),'LOWER AMPLITUDE',25,GOLD,True)
    text(d,(1430,578),'180 MPa',47,WHITE,True)
    if u>8.4: text(d,(1430,640),'→ 1,000,000 cycles',28,GOLD,True)
    text(d,(1430,737),'Same test conditions',25,MUTED)
    text(d,(85,886),'ILLUSTRATIVE DATA  •  Same material and test conditions  •  Not measured crank life.',24,GOLD)


def sn_limits(im,d,u):
    panel(d,(80,222,1040,853)); panel(d,(1070,222,1840,853))
    text(d,(115,255),'Real tests scatter around a trend',33,WHITE,True)
    pt=sn_chart(d,(175,365,970,730),scatter=True)
    text(d,(115,315),'Stress amplitude',24,CYAN)
    text(d,(565,790),'Cycles to failure (log scale)',26,CYAN,anchor='ma')
    text(d,(1110,260),'A fatigue limit is material dependent',29,WHITE,True)
    x,y,x2,y2=1160,380,1770,720
    arrow(d,(x,y2),(x,y-20),MUTED,3,12); arrow(d,(x,y2),(x2,y2),MUTED,3,12)
    steel=[(x+(x2-x)*p,y+175*(1-math.exp(-p*8))) for p in np.linspace(0,1,60)]
    alu=[(x+(x2-x)*p,y+60+250*p**.52) for p in np.linspace(0,1,60)]
    line(d,steel,CYAN,6); line(d,alu,GOLD,6)
    text(d,(1400,497),'Some steels',28,CYAN,True)
    text(d,(1400,681),'Aluminum alloys',28,GOLD,True)
    text(d,(1110,765),'Schematic trends; test conditions matter.',25,MUTED)
    text(d,(85,886),'ILLUSTRATIVE DATA  •  Not crank measurements  •  A curve does not predict an exact individual life.',24,GOLD)


def toughness(im,d,u):
    panel(d,(80,222,932,772),outline=CYAN); panel(d,(964,222,1840,772),outline=GOLD)
    text(d,(115,260),'CRACK-TIP LOADING',28,CYAN,True)
    formula(im,r'K_I',390,338,110,CYAN)
    text(d,(505,528),'Stress intensity factor',37,WHITE,True,anchor='ma')
    lines(d,(140,610),'Changes with load, crack length and geometry.',700,32,MUTED)
    text(d,(1000,260),'MATERIAL RESISTANCE',28,GOLD,True)
    formula(im,r'K_{Ic}',1265,338,110,GOLD)
    text(d,(1400,528),'Fracture toughness',37,WHITE,True,anchor='ma')
    lines(d,(1010,610),'Resistance to fracture from an existing crack.',740,32,MUTED)
    panel(d,(80,797,1840,904),fill='#142a3c')
    text(d,(110,815),'K_Ic applies to valid linear-elastic, plane-strain conditions.',30,GOLD,True)
    text(d,(110,859),'Plane strain: sufficient thickness constrains deformation through the thickness.',25,MUTED)


def formula_scene(im,d,u):
    chip(d,80,215,'MODE I  /  OPENING OF A CRACK',CYAN,25)
    fw,fh=formula_img(r'K_I=Y\sigma\sqrt{\pi a}',95).size
    formula(im,r'K_I=Y\sigma\sqrt{\pi a}',(W-fw)/2,320,95)
    for i,(sym,heading,desc,col) in enumerate([
        ('Y','Geometry factor','Part shape and crack geometry',BLUE),
        (r'\sigma','Applied stress','Tensile stress opening the crack',GOLD),
        ('a','Crack length','Defined for the chosen crack model',RED)]):
        x=80+i*595; panel(d,(x,540,x+568,830),outline=col)
        formula(im,sym,x+40,580,58,col)
        text(d,(x+142,594),heading,33,WHITE,True)
        lines(d,(x+36,711),desc,500,29,MUTED)
    text(d,(85,880),'Simplified linear-elastic relation. Y can change as the crack geometry changes.',26,MUTED)


def ki_changes(im,d,u):
    v1=smooth((u-.5)/3.2); v2=smooth((u-5.1)/3.4)
    for i in range(2):
        x=80+i*900; panel(d,(x,220,x+860,830))
        text(d,(x+35,250),'1  FIXED CRACK LENGTH' if i==0 else '2  FIXED STRESS',30,CYAN if i==0 else GOLD,True)
        a=.17 if i==0 else .12+.36*v2
        load=.5+.7*v1 if i==0 else .6
        plate(d,(x+115,442,x+745,632),a,load)
        if i==0:
            text(d,(x+35,753),'Stress ×2  →  K_I ×2',33,CYAN,True)
        else: text(d,(x+35,753),'Crack length ×4  →  K_I ×2',33,GOLD,True)
    text(d,(85,880),'RELATIVE EXAMPLE  •  Y held constant to isolate each effect  •  No material or crank test values.',25,MUTED)


def critical(im,d,u):
    chip(d,80,214,'LINEAR ELASTICITY + VALID PLANE STRAIN',GOLD,25)
    x,y,x2,y2=195,360,1260,760
    level=411
    panel(d,(80,304,1375,872))
    text(d,(122,320),'Maximum stress intensity, K_I,max',27,CYAN,True)
    arrow(d,(x,y2),(x,y-6),MUTED,3,12); arrow(d,(x,y2),(x2+25,y2),MUTED,3,12)
    dashed(d,(x,level),(x2,level),RED,4)
    text(d,(1045,367),'K_Ic',32,RED,True)
    def pt(p): return x+p*(x2-x),y2-80-310*p**1.55
    line(d,[pt(p) for p in np.linspace(0,1,100)],CYAN,6)
    critical_p=((y2-80-level)/310)**(1/1.55)
    progress=.1+(critical_p-.1)*smooth(u/7.0) if u<8.0 else .54+.05*math.sin(u*2)
    q=pt(progress); dot(d,*q,11,GOLD)
    text(d,(728,804),'Increasing crack length under cyclic loading',27,MUTED,anchor='ma')
    panel(d,(1410,304,1840,872))
    if u<8:
        text(d,(1440,349),'AT THE LIMIT',26,RED,True)
        formula(im,r'K_{I,max}=K_{Ic}',1440,420,37,RED)
        lines(d,(1440,540),'Rapid fracture may occur.',360,36,WHITE,True)
        lines(d,(1440,703),'Small crack-tip plastic zone; sufficient thickness.',360,25,MUTED)
    else:
        text(d,(1440,349),'BELOW THE LIMIT',25,GOLD,True)
        formula(im,r'K_{I,max}<K_{Ic}',1440,420,37,GOLD)
        lines(d,(1440,540),'Fatigue growth can still occur.',360,35,WHITE,True)
        lines(d,(1440,703),'Growth also depends on cyclic range, load ratio and environment.',360,24,MUTED)
        arrow(d,(1410,612),(q[0]+22,q[1]),GOLD,4,18)
    text(d,(85,889),'SCHEMATIC  •  Fracture toughness is not a fatigue-growth threshold.',24,GOLD)


def bicycle_scene(im,d,u):
    bb,ped=bike(d,280,215,1.15,phase=.4+u*.58,force=True)
    panel(d,(1420,255,1840,700))
    text(d,(1450,291),'THE CRANK',32,GOLD,True)
    lines(d,(1450,360),'The arm between the pedal and the drive axle.',360,35,WHITE,True)
    lines(d,(1450,550),'Pedal force changes as the rider pedals.',360,29,MUTED)
    arrow(d,(1430,695),(bb[0]+90,bb[1]-20),GOLD,4,18)
    text(d,(85,882),'Illustrated bicycle and motion  •  No specific model or service life is represented.',25,MUTED)


def bike_load(im,d,u):
    panel(d,(80,222,1840,864))
    x1,y1=450,542; x2,y2=1420,580
    d.rounded_rectangle((316,410,470,692),20,fill='#233c50',outline=EDGE,width=3)
    line(d,[(x1,y1),(x2,y2)],'#8196a7',145)
    for x,y,r in [(x1,y1,113),(x2,y2,78)]:
        dot(d,x,y,r,'#8196a7'); dot(d,x,y,r*.53,BG); ring(d,x,y,r*.55,MUTED,6)
    ring(d,x1,y1,130,RED,4); ring(d,x2,y2,99,RED,4)
    for k in range(4): line(d,[(920+k*14,568),(940+k*14,600)],BG,3)
    length=120+70*(.5+.5*math.sin(u*4))
    arrow(d,(x2,y2-100-length),(x2,y2-100),GOLD,10,28)
    text(d,(x2+43,300),'Repeated',29,GOLD,True); text(d,(x2+43,341),'pedal force',29,GOLD,True)
    arrow(d,(x1,755),(x1,655),CYAN,8,22)
    text(d,(204,330),'Axle connection',31,WHITE,True)
    arrow(d,(370,380),(405,443),RED,4,14)
    text(d,(1290,753),'Pedal threads',31,WHITE,True)
    text(d,(820,745),'Surface scratch',30,WHITE,True)
    arrow(d,(972,733),(963,610),RED,4,14)
    text(d,(85,887),'SCHEMATIC  •  Geometry changes, threads and damage can raise local stress.',25,MUTED)


def bike_crack(im,d,u):
    panel(d,(80,220,1075,872),fill='#03070b')
    px,py,pw,ph=place(im,'crank_fracture.jpg',(94,233,1061,859))
    d=ImageDraw.Draw(im)
    # Local positions refer to the source photographer's described dark/bright regions.
    def p(x,y): return px+x/1827*pw,py+y/1320*ph
    q=p(725,610); r=p(695,278)
    panel(d,(102,253,438,302),fill='#08141f',outline=EDGE,r=10)
    text(d,(118,263),'Real broken bicycle crank',23,WHITE,True)
    panel(d,(110,650,402,703),fill='#08141f',outline=EDGE,r=10)
    text(d,(125,660),'Fatigue-growth region',24,CYAN,True)
    arrow(d,(401,675),q,CYAN,4,14)
    panel(d,(666,335,1022,390),fill='#08141f',outline=EDGE,r=10)
    text(d,(684,346),'Final fast-fracture region',24,RED,True)
    arrow(d,(670,367),r,RED,4,14)
    panel(d,(1110,220,1840,872))
    text(d,(1140,260),'ACCUMULATED DAMAGE',28,GOLD,True)
    progress=clamp((u-1)/5)
    broken=u>=6.8
    plate(d,(1210,470,1750,655),.08+.67*progress,.6+.4*math.sin(u*5),broken,20*smooth((u-6.8)/.35))
    label='1  Initiation' if u<2 else ('2  Growth over cycles' if u<6.8 else '3  Rapid final fracture')
    text(d,(1470,773),label,32,RED if broken else CYAN,True,anchor='ma')
    text(d,(85,887),'Photo: Oxensepp, Wikimedia Commons, CC BY-SA 3.0  •  Resized and annotated; schematic at right.',23,MUTED)


def bike_link(im,d,u):
    panel(d,(80,222,932,857)); panel(d,(964,222,1840,857))
    text(d,(115,253),'S-N: fatigue-life trend',34,CYAN,True)
    pt=sn_chart(d,(195,375,845,730),scatter=False,labels=False)
    reading(d,pt,4,300,clamp(u/2.0),RED)
    reading(d,pt,6,180,clamp((u-1.3)/2.0),GOLD)
    text(d,(115,320),'Stress amplitude',26,MUTED)
    text(d,(520,774),'Cycles to failure (log)',28,MUTED,anchor='ma')
    text(d,(1000,253),'K_I: an existing crack',34,GOLD,True)
    formula(im,r'K_I=Y\sigma\sqrt{\pi a}',1100,327,46,GOLD)
    a=.13+.6*smooth((u-3.8)/3.1)
    plate(d,(1080,534,1720,673),a,.45)
    text(d,(1000,782),'Longer crack → higher stress intensity',27,WHITE,True)
    text(d,(85,880),'Illustrative, not crank test data. Use K_Ic only when linear-elastic plane-strain conditions apply.',24,MUTED)


def care(im,d,u):
    cards=[('01','Protect surfaces','Avoid scratches and impact damage.',CYAN),
           ('02','Notice changes','Unusual sounds or movement need attention.',GOLD),
           ('03','Inspect for cracks','Stop using a suspected damaged part.',RED)]
    for i,(n,title,body,c) in enumerate(cards):
        y=224+i*201; panel(d,(80,y,960,y+177),outline=c)
        text(d,(110,y+27),n,55,c,True)
        text(d,(222,y+28),title,37,WHITE,True)
        lines(d,(222,y+91),body,695,28,MUTED)
    panel(d,(995,224,1840,872))
    text(d,(1030,254),'REFERENCES + PHOTO CREDITS',28,GOLD,True)
    refs=[('MIT OpenCourseWare','Fatigue, David Roylance  •  ocw.mit.edu'),
          ('NASA','Fracture Control Handbook  •  standards.nasa.gov'),
          ('NIST: real titanium specimen','nist.gov/image/semti-6al-4vpng-0'),
          ('Oxensepp: real broken crank','Wikimedia Commons  •  File:0x-kurbel-def.jpg')]
    for i,(heading,url) in enumerate(refs):
        yy=323+i*108
        text(d,(1030,yy),heading,28,WHITE,True)
        text(d,(1030,yy+40),url,23,MUTED)
    text(d,(1030,770),'Crank photo: CC BY-SA 3.0; resized + annotated.',23,GOLD)
    text(d,(1030,804),'creativecommons.org/licenses/by-sa/3.0',23,MUTED)
    text(d,(1030,841),'Full links and scientific notes in the reference file.',22,MUTED)
    text(d,(85,886),'Small cracks deserve attention.',25,CYAN,True)


DRAWERS={'intro':intro,'loading':loading,'specimen':specimen,'growth':growth,
         'sn_axes':sn_axes,'sn_read':sn_read,'sn_limits':sn_limits,'toughness':toughness,
         'formula':formula_scene,'ki_changes':ki_changes,'critical':critical,
         'bike':bicycle_scene,'bike_load':bike_load,'bike_crack':bike_crack,
         'bike_link':bike_link,'care':care}


def frame(scene,t):
    im,d=base(scene,t)
    DRAWERS[scene['id']](im,d,t-scene['start'])
    caption(im,t)
    return im.convert('RGB')


def render_scene(scene):
    path=TMP/(scene['id']+'.mp4'); count=round((scene['end']-scene['start'])*FPS)
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
         '-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-',
         '-an','-c:v','libx264','-preset','fast','-crf','19','-threads','2',
         '-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for i in range(count):
        t=scene['start']+i/FPS
        proc.stdin.write(frame(scene,t).tobytes())
    proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError(f"Encoding failed: {scene['id']}")
    return scene['id'],path.stat().st_size


def previews():
    previews=TMP/'previews'; previews.mkdir(exist_ok=True)
    samples=[5,17,28,35,41,46,55,67,74,82,94,105,115,119,127,132,139,147,155,158.5,165,174]
    for t in samples:
        scene=next(s for s in SCENES if s['start']<=t<s['end'])
        frame(scene,t).save(previews/f'{t:05.1f}_{scene["id"]}.jpg',quality=92)
    thumbw=640; thumbh=360
    sheet=Image.new('RGB',(thumbw*3,(thumbh+40)*math.ceil(len(samples)/3)),BG)
    dd=ImageDraw.Draw(sheet)
    for i,t in enumerate(samples):
        scene=next(s for s in SCENES if s['start']<=t<s['end'])
        small=Image.open(previews/f'{t:05.1f}_{scene["id"]}.jpg').resize((thumbw,thumbh),Image.Resampling.LANCZOS)
        x=i%3*thumbw; y=i//3*(thumbh+40)
        sheet.paste(small,(x,y)); text(dd,(x+10,y+thumbh+3),f'{t:.1f}s  {scene["id"]}',24)
    sheet.save(TMP/'contact_sheet.jpg',quality=90)
    print(TMP/'contact_sheet.jpg',flush=True)


def render(workers):
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        futures=[ex.submit(render_scene,s) for s in SCENES]
        for f in concurrent.futures.as_completed(futures):
            name,size=f.result(); print(f'Rendered {name}: {size/1e6:.1f} MB',flush=True)
    listing=TMP/'concat.txt'
    listing.write_text('\n'.join("file '"+str(TMP/(s['id']+'.mp4'))+"'" for s in SCENES))
    target=OUT/'Fatigue_Failure_3min_75_25.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),
                    '-i',str(ROOT/'audio'/'narration_normalized.wav'),
                    '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k',
                    '-t','180','-movflags','+faststart',str(target)],check=True)
    print('Complete: '+str(target),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--preview',action='store_true')
    p.add_argument('--render',action='store_true'); p.add_argument('--workers',type=int,default=3)
    args=p.parse_args()
    if args.preview: previews()
    if args.render: render(args.workers)
    if not args.preview and not args.render: p.print_help()
