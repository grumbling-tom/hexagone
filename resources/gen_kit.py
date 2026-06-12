#!/usr/bin/env python3
"""Generate a low-fi Excalidraw wireframe kit at TRUE 1:1 scale (real UI dimensions)."""
import json, random

random.seed(11)
DARK="#1e1e1e"; GREY="#868e96"; WHITE="#ffffff"; BAR="#ced4da"; FAINT="#adb5bd"
HINT="#e0e0e0"; TRANS="transparent"
FONT=5
# 1:1 type scale (px)
T_CAP=12; T_SM=13; T_BODY=14; T_SUB=16; T_H3=18; T_H2=24; T_H1=30
els=[]; _idx=[0]; CUR=[None]
R3={"type":3}; R2={"type":2}

def idx():
    _idx[0]+=1; return "c"+format(_idx[0],'05d')
def sid():
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(21))
def seed(): return random.randint(1,2000000000)

def el(t,x,y,w,h,stroke=DARK,bg=TRANS,fill="solid",sw=2,ss="solid",rough=1,round_=None,groups=None,bound=None,extra=None):
    g = groups if groups is not None else ([CUR[0]] if CUR[0] else [])
    e={"id":sid(),"type":t,"x":float(x),"y":float(y),"width":float(w),"height":float(h),"angle":0,
       "strokeColor":stroke,"backgroundColor":bg,"fillStyle":fill,"strokeWidth":sw,"strokeStyle":ss,
       "roughness":rough,"opacity":100,"groupIds":g,"frameId":None,"index":idx(),"roundness":round_,
       "seed":seed(),"version":1,"versionNonce":seed(),"isDeleted":False,"boundElements":bound,
       "updated":1781280000000,"link":None,"locked":False}
    if extra: e.update(extra)
    els.append(e); return e

def rect(x,y,w,h,**k): return el("rectangle",x,y,w,h,**k)
def ellipse(x,y,w,h,**k): return el("ellipse",x,y,w,h,**k)
def text(x,y,s,size=T_BODY,color=DARK,align="left",groups=None):
    w=max(8,int(len(s)*size*0.55)); h=int(round(size*1.25))
    return el("text",x,y,w,h,stroke=color,bg=TRANS,groups=groups,extra={
        "text":s,"fontSize":size,"fontFamily":FONT,"textAlign":align,"verticalAlign":"top",
        "containerId":None,"originalText":s,"autoResize":True,"lineHeight":1.25})
def ctext(cx,cy,s,size=T_BODY,color=DARK,groups=None):
    w=max(8,int(len(s)*size*0.55)); h=int(round(size*1.25))
    return text(int(cx-w/2),int(cy-h/2),s,size,color,"center",groups)
def line(x,y,points,stroke=GREY,sw=2,bg=TRANS,round_=None,closed=False,fill="solid",groups=None):
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    return el("line",x,y,max(xs)-min(xs),max(ys)-min(ys),stroke=stroke,bg=bg,fill=fill,sw=sw,round_=round_,groups=groups,extra={
        "points":[[float(px),float(py)] for px,py in points],
        "startBinding":None,"endBinding":None,"startArrowhead":None,"endArrowhead":None,"polygon":closed})
def hline(x,y,w,stroke=GREY,sw=2): return line(x,y,[[0,0],[w,0]],stroke=stroke,sw=sw)
def bar(x,y,w,h=10,color=BAR): return rect(x,y,w,h,stroke=color,bg=color,round_=R3)

def panel(x,y,w,h,title):
    CUR[0]=sid()
    rect(x,y,w,h,stroke=DARK,bg=TRANS,ss="dotted")
    text(x+16,y+12,title,size=T_SUB,color=DARK)
    return (x,y,w,h)
def endp(): CUR[0]=None

X0=2333
CUR[0]=None
text(X0,1860,"HEXAGONE - 1:1 wireframe kit  ·  real UI dimensions, greyscale",size=T_H2,color=DARK)

# ============ ROW A : ATOMS (y=1930) ============
ay=1930
# Buttons
x,y,w,h=panel(X0,ay,300,230,"Buttons")
rect(x+20,y+48,120,40,stroke=GREY,bg=GREY,round_=R3); ctext(x+80,y+68,"Primary",T_BODY,WHITE)
rect(x+156,y+48,120,40,stroke=FAINT,bg="#e9ecef",round_=R3); ctext(x+216,y+68,"Disabled",T_BODY,FAINT)
rect(x+20,y+100,120,40,stroke=GREY,bg=WHITE,round_=R3); ctext(x+80,y+120,"Secondary",T_BODY,GREY)
text(x+160,y+110,"Tertiary",T_BODY,GREY); hline(x+160,y+132,66,stroke=GREY)
text(x+20,y+162,"h 40 · radius 8 · label 14",T_CAP,GREY)
endp()

# Toggles & radio
x,y,w,h=panel(X0+340,ay,300,290,"Toggles & radio")
rect(x+20,y+50,44,24,stroke=GREY,bg=GREY,round_=R3); ellipse(x+42,y+52,20,20,stroke=GREY,bg=WHITE); text(x+78,y+52,"On",T_BODY,DARK)
rect(x+20,y+92,44,24,stroke=GREY,bg=WHITE,round_=R3); ellipse(x+22,y+94,20,20,stroke=GREY,bg=WHITE); text(x+78,y+94,"Off",T_BODY,DARK)
ellipse(x+22,y+140,22,22,stroke=GREY,bg=WHITE); ellipse(x+28,y+146,10,10,stroke=GREY,bg=GREY); text(x+78,y+143,"Selected",T_BODY,DARK)
ellipse(x+22,y+182,22,22,stroke=GREY,bg=WHITE); text(x+78,y+185,"Unselected",T_BODY,DARK)
text(x+20,y+228,"track 44x24 · radio 22",T_CAP,GREY)
endp()

# Checkboxes
x,y,w,h=panel(X0+680,ay,230,210,"Checkboxes")
rect(x+20,y+52,20,20,stroke=GREY,bg=GREY,round_=R3); line(x+20,y+52,[[5,10],[9,15],[16,5]],stroke=WHITE,sw=2); text(x+52,y+52,"Checked",T_BODY,DARK)
rect(x+20,y+92,20,20,stroke=GREY,bg=WHITE,round_=R3); text(x+52,y+92,"Unchecked",T_BODY,DARK)
rect(x+20,y+132,20,20,stroke=FAINT,bg="#e9ecef",round_=R3); text(x+52,y+132,"Disabled",T_BODY,FAINT)
endp()

# Badges & tags
x,y,w,h=panel(X0+950,ay,290,210,"Badges & tags")
rect(x+20,y+52,52,24,stroke=GREY,bg=GREY,round_=R3); ctext(x+46,y+64,"NEW",T_CAP,WHITE)
rect(x+86,y+52,62,24,stroke=GREY,bg=WHITE,round_=R3); ctext(x+117,y+64,"draft",T_CAP,GREY)
ellipse(x+164,y+50,26,26,stroke=GREY,bg=GREY); ctext(x+177,y+63,"3",T_SM,WHITE)
rect(x+20,y+96,120,26,stroke=GREY,bg=WHITE,round_=R3); ellipse(x+28,y+103,12,12,stroke=GREY,bg=GREY); text(x+48,y+101,"with dot",T_SM,DARK)
text(x+20,y+150,"filled · outline · count",T_CAP,GREY)
endp()

# Media placeholders
x,y,w,h=panel(X0+1280,ay,320,210,"Media placeholders")
rect(x+20,y+52,24,24,stroke=GREY,bg=WHITE,round_=R3); line(x+20,y+52,[[0,0],[24,24]],stroke=GREY); line(x+44,y+52,[[0,0],[-24,24]],stroke=GREY)
text(x+20,y+84,"Icon 24",T_CAP,GREY)
ellipse(x+90,y+50,40,40,stroke=GREY,bg=WHITE); ctext(x+110,y+70,"TS",T_BODY,GREY); text(x+86,y+96,"Avatar 40",T_CAP,GREY)
rect(x+170,y+50,120,80,stroke=GREY,bg=WHITE,round_=R3); line(x+170,y+50,[[0,0],[120,80]],stroke=GREY); line(x+290,y+50,[[0,0],[-120,80]],stroke=GREY)
text(x+170,y+136,"Image 120x80",T_CAP,GREY)
endp()

# ============ ROW B : MOLECULES (y=2300) ============
by=2300
# Inputs
x,y,w,h=panel(X0,by,330,300,"Inputs")
text(x+20,y+46,"Email",T_SM,DARK)
rect(x+20,y+66,290,40,stroke=GREY,bg=WHITE,round_=R3); text(x+32,y+78,"you@example.com",T_BODY,FAINT)
text(x+20,y+112,"We'll never share it.",T_CAP,GREY)
text(x+20,y+160,"Email",T_SM,DARK)
rect(x+20,y+180,290,40,stroke="#495057",bg=WHITE,sw=3,round_=R3); text(x+32,y+192,"not-an-email",T_BODY,DARK)
text(x+20,y+226,"!  Enter a valid email",T_CAP,"#495057")
text(x+20,y+262,"field h 40 · default + error",T_CAP,GREY)
endp()

# Stat / KPI
x,y,w,h=panel(X0+370,by,220,160,"Stat / KPI")
text(x+20,y+44,"142",T_H1,DARK)
text(x+20,y+90,"HEXES CLAIMED",T_CAP,GREY)
text(x+20,y+112,"+20 this week",T_SM,DARK)
endp()

# List row
x,y,w,h=panel(X0+630,by,360,250,"List row")
def list_row(rx,ry,title,sub,gain):
    ellipse(rx,ry,40,40,stroke=GREY,bg=WHITE)
    text(rx+52,ry+2,title,T_BODY,DARK); text(rx+52,ry+22,sub,T_CAP,GREY)
    rect(rx+250,ry+8,48,24,stroke=GREY,bg=WHITE,round_=R3); ctext(rx+274,ry+20,gain,T_SM,DARK)
list_row(x+20,y+54,"Riverside loop","8.4 km · 41 min","+6"); hline(x+20,y+106,320,stroke="#dee2e6")
list_row(x+20,y+120,"Park sprints","5.1 km · 26 min","+3"); hline(x+20,y+172,320,stroke="#dee2e6")
list_row(x+20,y+186,"Long Sunday","16.2 km · 84 min","+9")
endp()

# Tabs, segmented & search
x,y,w,h=panel(X0+1030,by,330,300,"Tabs, segmented & search")
rect(x+20,y+50,290,36,stroke=GREY,bg=WHITE,round_=R3)
rect(x+20,y+50,98,36,stroke=GREY,bg=GREY,round_=R3); ctext(x+69,y+68,"Map",T_SM,WHITE)
line(x+118,y+50,[[0,0],[0,36]],stroke=GREY); line(x+214,y+50,[[0,0],[0,36]],stroke=GREY)
ctext(x+166,y+68,"Stats",T_SM,GREY); ctext(x+262,y+68,"Feed",T_SM,GREY)
text(x+20,y+108,"Overview",T_BODY,DARK); hline(x+20,y+128,70,stroke=DARK,sw=2)
text(x+110,y+108,"Routes",T_BODY,GREY); text(x+196,y+108,"Awards",T_BODY,GREY)
rect(x+20,y+156,290,40,stroke=GREY,bg=WHITE,round_=R3)
ellipse(x+34,y+167,16,16,stroke=GREY,bg=WHITE); line(x+47,y+180,[[0,0],[7,7]],stroke=GREY)
text(x+62,y+168,"Search runs…",T_BODY,FAINT)
endp()

# ============ ROW C : CARD + ORGANISMS (y=2670) ============
cy=2670
# Card
x,y,w,h=panel(X0,cy,320,300,"Card")
cx0,cy0,cw,chh=x+20,y+46,280,232
rect(cx0,cy0,cw,chh,stroke=GREY,bg=WHITE,round_=R3)
rect(cx0,cy0,cw,96,stroke=GREY,bg="#e9ecef"); line(cx0,cy0,[[0,0],[cw,96]],stroke=FAINT); line(cx0+cw,cy0,[[0,0],[-cw,96]],stroke=FAINT)
text(cx0+16,cy0+108,"Riverside loop",T_SUB,DARK)
bar(cx0+16,cy0+136,cw-90,10); bar(cx0+16,cy0+154,cw-140,10)
rect(cx0+16,cy0+180,108,36,stroke=GREY,bg=GREY,round_=R3); ctext(cx0+70,cy0+198,"View run",T_SM,WHITE)
endp()

# Modal / dialog
x,y,w,h=panel(X0+360,cy,340,290,"Modal / dialog")
rect(x+18,y+44,w-36,h-62,stroke=FAINT,bg="#f1f3f5",round_=R3)
dx,dy,dw,dh=x+44,y+78,w-88,h-140
rect(dx,dy,dw,dh,stroke=GREY,bg=WHITE,round_=R3)
text(dx+16,dy+16,"Delete run?",T_SUB,DARK)
line(dx+dw-32,dy+18,[[0,0],[14,14]],stroke=GREY); line(dx+dw-18,dy+18,[[0,0],[-14,14]],stroke=GREY)
bar(dx+16,dy+52,dw-32,10); bar(dx+16,dy+70,dw-80,10)
rect(dx+dw-176,dy+dh-50,84,34,stroke=GREY,bg=WHITE,round_=R3); ctext(dx+dw-134,dy+dh-33,"Cancel",T_SM,GREY)
rect(dx+dw-84,dy+dh-50,72,34,stroke=GREY,bg=GREY,round_=R3); ctext(dx+dw-48,dy+dh-33,"Delete",T_SM,WHITE)
endp()

# Top navigation (wide)
x,y,w,h=panel(X0+720,cy,740,110,"Top navigation")
rect(x+20,y+42,700,56,stroke=GREY,bg=WHITE,round_=R3)
rect(x+36,y+58,32,32,stroke=GREY,bg=GREY,round_=R3); text(x+78,y+62,"Hexagone",T_SUB,DARK)
text(x+330,y+64,"Map",T_BODY,DARK); text(x+400,y+64,"Activities",T_BODY,GREY); text(x+510,y+64,"Goals",T_BODY,GREY)
ellipse(x+668,y+54,32,32,stroke=GREY,bg=WHITE); ctext(x+684,y+70,"T",T_SM,GREY)
endp()

# Table (under nav)
x,y,w,h=panel(X0+720,cy+150,740,300,"Table")
tx=x+20; tw=700
rect(tx,y+46,tw,38,stroke=GREY,bg="#e9ecef")
for i,c in enumerate(["Date","Activity","Dist","Hexes"]):
    text(tx+14+i*175,y+55,c,T_SM,DARK)
rows=[["12 Jun","Riverside loop","8.4","+6"],["10 Jun","Park sprints","5.1","+3"],
      ["08 Jun","Long Sunday","16.2","+9"],["06 Jun","Commute dash","4.0","+2"],["04 Jun","Tempo intervals","9.3","+5"]]
ry=y+84
for r in rows:
    for i,c in enumerate(r): text(tx+14+i*175,ry+11,c,T_SM,GREY if i else DARK)
    hline(tx,ry+38,tw,stroke="#dee2e6"); ry+=40
for i in range(1,4): line(tx+i*175,y+46,[[0,0],[0,38+len(rows)*40]],stroke="#dee2e6")
endp()

# ============ ROW D : SYSTEM / TOKENS (y=3000) ============
ty=3000
# Spacing scale
x,y,w,h=panel(X0,ty,240,360,"Spacing scale")
cc=y+44
for s in [4,8,12,16,24,32,48,64]:
    rect(x+20,cc,s,s,stroke=GREY,bg=GREY,round_=R3); text(x+96,cc+max(0,(s-14)//2)-2,f"{s}px",T_SM,DARK); cc+=s+14
endp()
# Type scale
x,y,w,h=panel(X0+280,ty,360,360,"Type scale")
cc=y+40
for s in [30,24,20,18,16,14,13,12]:
    text(x+20,cc,"Aa  The quick run",s,DARK); text(x+300,cc+max(0,(s-13)//2),f"{s}",T_SM,GREY); cc+=int(s*1.25)+12
endp()
# Grey ramp
x,y,w,h=panel(X0+680,ty,330,360,"Grey ramp")
cc=y+44
for hexc,role in [("#f1f3f5","border / bg"),("#dee2e6","dividers"),("#adb5bd","disabled / hint"),
                  ("#868e96","secondary text"),("#495057","body text"),("#212529","headings")]:
    rect(x+20,cc,56,36,stroke="#cccccc",bg=hexc,round_=R3); text(x+92,cc+2,hexc,T_SM,DARK); text(x+92,cc+20,role,T_CAP,GREY); cc+=48
endp()

# ============ ARTBOARDS : real 1:1 device sizes ============
CUR[0]=None
text(X0,3450,"Artboards - 1:1 device sizes, compose your design inside",size=T_H2,color=DARK)
# Desktop 1440 x 900
CUR[0]=sid()
ax,ay2,aw,ah=X0,3530,1440,900
text(ax,ay2-30,"Desktop - 1440 x 900",T_SUB,GREY)
rect(ax,ay2,aw,ah,stroke=GREY,bg=WHITE,round_=R3)
rect(ax,ay2,aw,56,stroke=GREY,bg="#e9ecef")
for i in range(3): ellipse(ax+20+i*24,ay2+21,14,14,stroke=GREY,bg=WHITE)
rect(ax+110,ay2+14,aw-150,28,stroke=GREY,bg=WHITE,round_=R3); text(ax+126,ay2+19,"hexagone.app/dashboard",T_BODY,FAINT)
ctext(ax+aw/2,ay2+56+(ah-56)/2,"compose your design here",T_H3,HINT)
CUR[0]=None
# Mobile 390 x 844
CUR[0]=sid()
mx,my,mw,mh=X0+1500,3530,390,844
text(mx,my-30,"Mobile - 390 x 844",T_SUB,GREY)
rect(mx,my,mw,mh,stroke=GREY,bg=WHITE,round_=R3)
rect(int(mx+mw/2-55),my+14,110,26,stroke=DARK,bg=DARK,round_=R3)
rect(int(mx+mw/2-60),my+mh-20,120,7,stroke=FAINT,bg=FAINT,round_=R3)
ctext(mx+mw/2,my+mh/2,"compose here",T_H3,HINT)
CUR[0]=None

# ============================================================
# EXTENDED SET : states · forms · feedback · navigation
# ============================================================
import math
def pbtn(bx,by,label,bw=120):
    rect(bx,by,bw,40,stroke=GREY,bg=GREY,round_=R3); ctext(bx+bw/2,by+20,label,T_BODY,WHITE)
def sbtn(bx,by,label,bw=120):
    rect(bx,by,bw,40,stroke=GREY,bg=WHITE,round_=R3); ctext(bx+bw/2,by+20,label,T_BODY,GREY)
def iconx(ix,iy,s=60,stroke=GREY):
    rect(ix,iy,s,s,stroke=stroke,bg=WHITE,round_=R3); line(ix,iy,[[0,0],[s,s]],stroke=stroke); line(ix+s,iy,[[0,0],[-s,s]],stroke=stroke)
def tick(tx,ty,col=WHITE,sw=2,sc=1.0):
    line(tx,ty,[[0,5*sc],[4*sc,9*sc],[11*sc,-1*sc]],stroke=col,sw=sw)
def arc(cx,cy,r,a0,a1,stroke=GREY,sw=2,n=26):
    pts=[(cx+r*math.cos(math.radians(a)),cy+r*math.sin(math.radians(a))) for a in [a0+(a1-a0)*i/n for i in range(n+1)]]
    ox,oy=pts[0]; return line(ox,oy,[[px-ox,py-oy] for px,py in pts],stroke=stroke,sw=sw)

CUR[0]=None
text(X0,4540,"EXTENDED - states · forms · feedback · navigation",size=T_H2,color=DARK)

# ---- STATES (y=4610) ----
sy2=4610
x,y,w,h=panel(X0,sy2,300,300,"Empty state")
iconx(x+w//2-30,y+54,60)
ctext(x+w/2,y+132,"No runs yet",T_SUB,DARK)
ctext(x+w/2,y+158,"Upload a GPX to claim hexes",T_CAP,GREY)
pbtn(x+w//2-60,y+190,"Upload a run")
endp()

x,y,w,h=panel(X0+340,sy2,300,300,"Loading (skeleton)")
ellipse(x+24,y+54,40,40,stroke=BAR,bg=BAR)
bar(x+76,y+58,150,12); bar(x+76,y+80,100,10)
bar(x+24,y+118,w-48,12); bar(x+24,y+140,w-48,12); bar(x+24,y+162,180,12)
arc(x+w/2,y+232,16,-90,200,stroke=GREY,sw=3)
ctext(x+w/2,y+262,"loading…",T_CAP,GREY)
endp()

x,y,w,h=panel(X0+680,sy2,300,300,"Error state")
line(x+w//2-30,y+54,[[30,0],[60,56],[0,56],[30,0]],stroke=GREY,sw=2,closed=True)
ctext(x+w/2,y+78,"!",T_H2,DARK)
ctext(x+w/2,y+132,"Couldn't load runs",T_SUB,DARK)
ctext(x+w/2,y+158,"Check your connection",T_CAP,GREY)
sbtn(x+w//2-60,y+190,"Try again")
endp()

x,y,w,h=panel(X0+1020,sy2,300,300,"Success state")
ellipse(x+w//2-30,y+54,60,60,stroke=GREY,bg=WHITE); tick(x+w//2-14,y+78,col=GREY,sw=3,sc=2.4)
ctext(x+w/2,y+132,"Run uploaded",T_SUB,DARK)
ctext(x+w/2,y+158,"+6 hexes claimed",T_CAP,GREY)
pbtn(x+w//2-65,y+190,"View on map",130)
endp()

# ---- FORM CONTROLS (y=4970 / 5330) ----
fy=4970
x,y,w,h=panel(X0,fy,320,300,"Select / dropdown")
text(x+20,y+46,"Activity type",T_SM,DARK)
rect(x+20,y+66,280,40,stroke=GREY,bg=WHITE,round_=R3); text(x+32,y+78,"Choose…",T_BODY,FAINT)
line(x+278,y+82,[[0,0],[6,7],[12,0]],stroke=GREY,sw=2)
rect(x+20,y+114,280,108,stroke=GREY,bg=WHITE,round_=R3)
rect(x+24,y+118,272,32,stroke=GREY,bg="#e9ecef",round_=R3); text(x+34,y+125,"Run",T_BODY,DARK)
text(x+34,y+159,"Walk",T_BODY,DARK); text(x+34,y+191,"Ride",T_BODY,DARK)
endp()

x,y,w,h=panel(X0+360,fy,300,300,"Textarea")
text(x+20,y+46,"Notes",T_SM,DARK)
rect(x+20,y+66,260,150,stroke=GREY,bg=WHITE,round_=R3)
bar(x+32,y+80,180,10); bar(x+32,y+100,220,10); bar(x+32,y+120,140,10)
line(x+264,y+200,[[0,12],[12,0]],stroke=FAINT); line(x+270,y+206,[[0,6],[6,0]],stroke=FAINT)
endp()

x,y,w,h=panel(X0+700,fy,300,300,"Slider & stepper")
text(x+20,y+46,"Distance goal",T_SM,DARK)
hline(x+24,y+86,256,stroke="#dee2e6",sw=4)
hline(x+24,y+86,150,stroke=GREY,sw=4)
ellipse(x+166,y+76,20,20,stroke=GREY,bg=WHITE)
text(x+24,y+104,"12 km",T_CAP,GREY)
text(x+20,y+150,"Reps",T_SM,DARK)
rect(x+20,y+170,40,40,stroke=GREY,bg=WHITE,round_=R3); ctext(x+40,y+190,"-",T_H3,DARK)
rect(x+66,y+170,64,40,stroke=GREY,bg=WHITE,round_=R3); ctext(x+98,y+190,"3",T_SUB,DARK)
rect(x+136,y+170,40,40,stroke=GREY,bg=WHITE,round_=R3); ctext(x+156,y+190,"+",T_H3,DARK)
endp()

x,y,w,h=panel(X0+1040,fy,320,300,"File upload (dropzone)")
rect(x+20,y+50,280,160,stroke=GREY,bg=WHITE,ss="dashed",round_=R3)
line(x+w//2,y+86,[[0,40],[0,0]],stroke=GREY,sw=3)
line(x+w//2-12,y+98,[[12,-12],[0,0],[-12,12]],stroke=GREY,sw=3)
ctext(x+w/2,y+138,"Drag a GPX file here",T_BODY,DARK)
ctext(x+w/2,y+162,"or click to browse",T_CAP,GREY)
endp()

dy2=5330
x,y,w,h=panel(X0,dy2,300,220,"Date field")
text(x+20,y+46,"Date",T_SM,DARK)
rect(x+20,y+66,260,40,stroke=GREY,bg=WHITE,round_=R3); text(x+32,y+78,"12 Jun 2026",T_BODY,DARK)
rect(x+250,y+74,20,20,stroke=GREY,bg=WHITE,round_=R3); hline(x+250,y+80,20,stroke=GREY)
endp()

x,y,w,h=panel(X0+340,dy2,330,290,"Field group (anatomy)")
text(x+20,y+44,"Email *",T_SM,DARK); text(x+200,y+44,"label + required",T_CAP,FAINT)
rect(x+20,y+64,290,40,stroke=GREY,bg=WHITE,round_=R3); text(x+32,y+76,"you@example.com",T_BODY,FAINT)
text(x+20,y+110,"We'll send your weekly summary.",T_CAP,GREY); text(x+200,y+110,"helper",T_CAP,FAINT)
rect(x+20,y+150,290,40,stroke="#495057",bg=WHITE,sw=3,round_=R3); text(x+32,y+162,"not-an-email",T_BODY,DARK)
text(x+20,y+196,"!  Enter a valid email",T_CAP,"#495057"); text(x+200,y+196,"error",T_CAP,FAINT)
endp()

# ---- FEEDBACK & DATA VIZ (y=5680 / 5990) ----
gy=5680
x,y,w,h=panel(X0,gy,320,260,"Toast & tooltip")
rect(x+24,y+56,272,44,stroke=DARK,bg=DARK,round_=R3)
tick(x+38,y+72,col=WHITE,sw=2,sc=1.4); text(x+58,y+68,"Run uploaded",T_BODY,WHITE); text(x+232,y+68,"UNDO",T_SM,BAR)
rect(x+90,y+150,120,34,stroke=DARK,bg=DARK,round_=R3); ctext(x+150,y+167,"Claimed hex",T_CAP,WHITE)
line(x+140,y+184,[[0,0],[10,0],[5,8],[0,0]],stroke=DARK,bg=DARK,closed=True,fill="solid")
text(x+24,y+208,"transient · auto-dismiss",T_CAP,GREY)
endp()

x,y,w,h=panel(X0+360,gy,340,260,"Inline alerts")
def alertbar(ax,ay,bstroke,sym,t1):
    rect(ax,ay,300,46,stroke=bstroke,bg="#f1f3f5",round_=R3)
    ellipse(ax+12,ay+13,20,20,stroke=bstroke,bg=WHITE); ctext(ax+22,ay+24,sym,T_SM,bstroke)
    text(ax+44,ay+14,t1,T_BODY,DARK)
alertbar(x+20,y+52,GREY,"i","New season starts Monday")
alertbar(x+20,y+108,"#2f9e44","✓","Run saved")
alertbar(x+20,y+164,"#495057","!","Upload failed — retry")
endp()

x,y,w,h=panel(X0+720,gy,300,260,"Progress & goal meter")
text(x+20,y+46,"Weekly goal",T_SM,DARK)
rect(x+20,y+66,260,12,stroke=BAR,bg=BAR,round_=R3); rect(x+20,y+66,156,12,stroke=GREY,bg=GREY,round_=R3)
text(x+20,y+84,"3 / 5 runs",T_CAP,GREY)
ellipse(x+w//2-34,y+118,68,68,stroke="#dee2e6",bg=TRANS,sw=8)
arc(x+w/2,y+152,34,-90,162,stroke=GREY,sw=8)
ctext(x+w/2,y+150,"70%",T_SM,DARK)
endp()

x,y,w,h=panel(X0+1040,gy,360,280,"Charts (placeholders)")
# bar chart
line(x+30,y+50,[[0,0],[0,110],[150,110]],stroke=GREY,sw=2)
for i,bh in enumerate([40,70,30,90,55,75]):
    rect(x+42+i*20,y+160-bh,14,bh,stroke=GREY,bg=BAR)
text(x+30,y+170,"bar",T_CAP,GREY)
# line chart
line(x+210,y+50,[[0,0],[0,110],[130,110]],stroke=GREY,sw=2)
line(x+216,y+140,[[0,0],[24,-30],[48,-12],[72,-48],[96,-26],[120,-58]],stroke=GREY,sw=2)
text(x+210,y+170,"line",T_CAP,GREY)
# ring
ellipse(x+60,y+196,52,52,stroke="#dee2e6",bg=TRANS,sw=7); arc(x+86,y+222,26,-90,120,stroke=GREY,sw=7)
text(x+130,y+212,"ring / gauge",T_CAP,GREY)
endp()

hy=5990
x,y,w,h=panel(X0,hy,420,220,"Streak heatmap")
shades=["#f1f3f5","#dee2e6","#adb5bd","#868e96","#495057"]
for c in range(13):
    for r in range(7):
        sh=shades[(c*3+r*5+ (c%4)) % len(shades)]
        rect(x+24+c*28,y+50+r*22,18,18,stroke="#e9ecef",bg=sh,round_=R3)
text(x+24,y+204,"less",T_CAP,GREY); text(x+360,y+204,"more",T_CAP,GREY)
endp()

# ---- NAVIGATION (y=6260 / 6420) ----
ny=6260
x,y,w,h=panel(X0,ny,360,110,"Breadcrumb")
text(x+20,y+54,"Home",T_BODY,GREY); text(x+86,y+54,">",T_BODY,FAINT)
text(x+108,y+54,"Activities",T_BODY,GREY); text(x+196,y+54,">",T_BODY,FAINT)
text(x+218,y+54,"Riverside loop",T_BODY,DARK)
endp()

x,y,w,h=panel(X0+400,ny,330,110,"Pagination")
sbtn(x+20,y+50,"‹",36)
rect(x+64,y+50,36,36,stroke=GREY,bg=GREY,round_=R3); ctext(x+82,y+68,"1",T_BODY,WHITE)
sbtn(x+108,y+50,"2",36); sbtn(x+152,y+50,"3",36); text(x+196,y+60,"…",T_BODY,GREY); sbtn(x+220,y+50,"9",36)
sbtn(x+264,y+50,"›",36)
endp()

x,y,w,h=panel(X0+760,ny,470,110,"Stepper (multi-step)")
steps=[("1",True),("2",False),("3",False),("4",False)]
sx=x+30
for i,(n,active) in enumerate(steps):
    cx=sx+i*120
    if i>0: hline(cx-86,y+62,76,stroke="#dee2e6",sw=3)
    if i==0:
        ellipse(cx-14,y+48,28,28,stroke=GREY,bg=GREY); tick(cx-7,y+58,col=WHITE,sw=2,sc=1.2)
    elif i==1:
        ellipse(cx-14,y+48,28,28,stroke=GREY,bg=WHITE,sw=3); ctext(cx,y+62,n,T_SM,DARK)
    else:
        ellipse(cx-14,y+48,28,28,stroke=FAINT,bg=WHITE); ctext(cx,y+62,n,T_SM,FAINT)
    ctext(cx,y+88,["Upload","Review","Confirm","Done"][i],T_CAP,DARK if i<2 else FAINT)
endp()

ny2=6420
x,y,w,h=panel(X0,ny2,240,360,"Sidebar")
rect(x+20,y+44,32,32,stroke=GREY,bg=GREY,round_=R3); text(x+62,y+50,"Hexagone",T_SM,DARK)
items=[("Dashboard",False),("Map",True),("Activities",False),("Goals",False),("Settings",False)]
iy=y+96
for label,active in items:
    if active: rect(x+16,iy-6,208,36,stroke=GREY,bg="#e9ecef",round_=R3)
    rect(x+24,iy,18,18,stroke=GREY if active else FAINT,bg=WHITE,round_=R3)
    text(x+52,iy-1,label,T_BODY,DARK if active else GREY); iy+=44
endp()

x,y,w,h=panel(X0+280,ny2,260,290,"Overflow menu")
rect(x+20,y+46,40,36,stroke=GREY,bg=WHITE,round_=R3)
for i in range(3): ellipse(x+30+i*8,y+62,4,4,stroke=GREY,bg=GREY)
rect(x+20,y+94,200,150,stroke=GREY,bg=WHITE,round_=R3)
text(x+34,y+106,"Edit run",T_BODY,DARK)
text(x+34,y+138,"Share",T_BODY,DARK)
text(x+34,y+170,"Download GPX",T_BODY,DARK)
hline(x+24,y+202,192,stroke="#dee2e6")
text(x+34,y+212,"Delete",T_BODY,"#495057")
endp()

x,y,w,h=panel(X0+560,ny2,390,140,"Mobile bottom tab bar")
rect(x+20,y+44,350,76,stroke=GREY,bg=WHITE,round_=R3)
tabs=[("Map",True),("Activity",False),("Goals",False),("You",False)]
for i,(label,active) in enumerate(tabs):
    tcx=x+20+44+i*88
    col=DARK if active else FAINT
    rect(tcx-11,y+58,22,22,stroke=col,bg="#e9ecef" if active else WHITE,round_=R3)
    ctext(tcx,y+98,label,T_CAP,col)
endp()

x,y,w,h=panel(X0+560,ny2+180,390,120,"Mobile app bar")
rect(x+20,y+44,350,52,stroke=GREY,bg=WHITE,round_=R3)
line(x+40,y+60,[[8,0],[0,10],[8,20]],stroke=DARK,sw=2)
ctext(x+20+175,y+70,"Riverside loop",T_SUB,DARK)
for i in range(3): ellipse(x+336,y+60+i*7,4,4,stroke=GREY,bg=GREY)
endp()

scene={"type":"excalidraw","version":2,"source":"https://excalidraw.com",
       "elements":els,"appState":{"gridSize":None,"viewBackgroundColor":"#ffffff"},"files":{}}
with open("hexagone-wireframe-kit.excalidraw","w") as f:
    json.dump(scene,f)
print("elements:",len(els))
