#!/usr/bin/env python3
"""Worked example: the Hexagone dashboard composed inside a desktop artboard from the 1:1 kit."""
import json, random, math
random.seed(21)
DARK="#1e1e1e"; GREY="#868e96"; WHITE="#ffffff"; BAR="#ced4da"; FAINT="#adb5bd"
CARD="#d0d5da"; LINE="#e3e6e9"; HINT="#e0e0e0"; TRANS="transparent"
FONT=5
T_CAP=12; T_SM=13; T_BODY=14; T_SUB=16; T_H3=18; T_H2=24; T_H1=30
els=[]; _idx=[0]; CUR=[None]
R3={"type":3}

def idx(): _idx[0]+=1; return "c"+format(_idx[0],'05d')
def sid(): return ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(21))
def seed(): return random.randint(1,2000000000)
def el(t,x,y,w,h,stroke=DARK,bg=TRANS,fill="solid",sw=2,ss="solid",rough=1,round_=None,groups=None,extra=None):
    g = groups if groups is not None else ([CUR[0]] if CUR[0] else [])
    e={"id":sid(),"type":t,"x":float(x),"y":float(y),"width":float(w),"height":float(h),"angle":0,
       "strokeColor":stroke,"backgroundColor":bg,"fillStyle":fill,"strokeWidth":sw,"strokeStyle":ss,
       "roughness":rough,"opacity":100,"groupIds":g,"frameId":None,"index":idx(),"roundness":round_,
       "seed":seed(),"version":1,"versionNonce":seed(),"isDeleted":False,"boundElements":None,
       "updated":1781280000000,"link":None,"locked":False}
    if extra: e.update(extra)
    els.append(e); return e
def rect(x,y,w,h,**k): return el("rectangle",x,y,w,h,**k)
def ellipse(x,y,w,h,**k): return el("ellipse",x,y,w,h,**k)
def text(x,y,s,size=T_BODY,color=DARK,align="left"):
    w=max(8,int(len(s)*size*0.55)); h=int(round(size*1.25))
    return el("text",x,y,w,h,stroke=color,bg=TRANS,extra={"text":s,"fontSize":size,"fontFamily":FONT,
        "textAlign":align,"verticalAlign":"top","containerId":None,"originalText":s,"autoResize":True,"lineHeight":1.25})
def ctext(cx,cy,s,size=T_BODY,color=DARK):
    w=max(8,int(len(s)*size*0.55)); h=int(round(size*1.25)); return text(int(cx-w/2),int(cy-h/2),s,size,color,"center")
def line(x,y,points,stroke=GREY,sw=2,bg=TRANS,closed=False,fill="solid"):
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    return el("line",x,y,max(xs)-min(xs),max(ys)-min(ys),stroke=stroke,bg=bg,fill=fill,sw=sw,extra={
        "points":[[float(px),float(py)] for px,py in points],"startBinding":None,"endBinding":None,
        "startArrowhead":None,"endArrowhead":None,"polygon":closed})
def hline(x,y,w,stroke=GREY,sw=2): return line(x,y,[[0,0],[w,0]],stroke=stroke,sw=sw)
def bar(x,y,w,h=10,color=BAR): return rect(x,y,w,h,stroke=color,bg=color,round_=R3)
def pbtn(bx,by,label,bw=150):
    rect(bx,by,bw,40,stroke=GREY,bg=GREY,round_=R3); ctext(bx+bw/2,by+20,label,T_BODY,WHITE)
def card(cx,cy,cw,ch):
    rect(cx,cy,cw,ch,stroke=CARD,bg=WHITE,round_=R3)

# ---------- artboard ----------
AX,AY,AW,AH=240,200,1440,1180
PAD=32; IX=AX+PAD; IW=AW-2*PAD
CUR[0]=None
text(AX,AY-34,"Hexagone - dashboard worked example  ·  built from the 1:1 kit  ·  Desktop 1440",size=T_H2,color=DARK)
CUR[0]=sid()
rect(AX,AY,AW,AH,stroke=GREY,bg=WHITE,round_=R3)

# ---------- top nav ----------
hline(AX,AY+64,AW,stroke=LINE)
rect(IX,AY+16,32,32,stroke=GREY,bg=GREY,round_=R3); text(IX+44,AY+22,"Hexagone",T_SUB,DARK)
text(AX+560,AY+24,"Dashboard",T_BODY,DARK); hline(AX+560,AY+46,82,stroke=DARK,sw=2)
text(AX+664,AY+24,"Map",T_BODY,GREY); text(AX+730,AY+24,"Activities",T_BODY,GREY); text(AX+836,AY+24,"Goals",T_BODY,GREY)
rect(AX+AW-220,AY+16,120,32,stroke=GREY,bg=WHITE,round_=R3)
ellipse(AX+AW-210,AY+24,16,16,stroke=GREY,bg=WHITE); line(AX+AW-197,AY+37,[[0,0],[7,7]],stroke=GREY)
text(AX+AW-178,AY+25,"Search",T_SM,FAINT)
ellipse(AX+AW-80,AY+12,40,40,stroke=GREY,bg=WHITE); ctext(AX+AW-60,AY+32,"T",T_SM,GREY)

# ---------- header ----------
text(IX,AY+86,"This week",T_H1,DARK)
text(IX,AY+126,"Mon 8 - Sun 14 Jun · 4 activities",T_BODY,GREY)
pbtn(AX+AW-PAD-160,AY+96,"+ Upload a run",160)

# ---------- KPI row ----------
ky=AY+180; cw=(IW-3*24)//4
def statcard(cx,label,num,delta):
    card(cx,ky,cw,96)
    text(cx+18,ky+16,label,T_CAP,GREY)
    text(cx+18,ky+34,num,T_H1,DARK)
    text(cx+18,ky+74,delta,T_CAP,GREY)
for i,(l,n,d) in enumerate([("HEXES CLAIMED","142","+20 this week"),("DISTANCE","318 km","+33.7 km"),
                            ("AVG PACE","5:08 /km","6s faster"),("DAY STREAK","12","keep it going")]):
    statcard(IX+i*(cw+24),l,n,d)

# ---------- main grid ----------
GT=AY+304
LCW=884; RCX=IX+LCW+24; RCW=IW-LCW-24

# Map card
mc_x,mc_y,mc_w,mc_h=IX,GT,LCW,320
card(mc_x,mc_y,mc_w,mc_h)
text(mc_x+20,mc_y+16,"Coverage map",T_SUB,DARK)
for j,(lab,sw) in enumerate([("You","#868e96"),("Others","#dfe3e7"),("Open",WHITE)]):
    lx=mc_x+mc_w-220+j*70
    rect(lx,mc_y+18,12,12,stroke=GREY,bg=sw,round_=R3); text(lx+18,mc_y+15,lab,T_CAP,GREY)
hline(mc_x,mc_y+48,mc_w,stroke=LINE)
# hex grid inside card
R=18; dxh=math.sqrt(3)*R; dyh=1.5*R
gx0,gy0,gx1,gy1=mc_x+10,mc_y+58,mc_x+mc_w-10,mc_y+mc_h-12
home=(mc_x+mc_w*0.40,mc_y+mc_h*0.58); rival=(mc_x+mc_w*0.78,mc_y+mc_h*0.40)
def hexpts(cx,cy):
    return [[cx+R*math.cos(math.radians(60*i-90)),cy+R*math.sin(math.radians(60*i-90))] for i in range(6)]
claimed_centers=[]
r=0; cy=gy0
while cy<gy1+R:
    c=0; cx=gx0+(dxh/2 if r%2 else 0)
    while cx<gx1+R:
        if gx0<=cx<=gx1 and gy0<=cy<=gy1:
            dh=math.hypot(cx-home[0],cy-home[1]); dr=math.hypot(cx-rival[0],cy-rival[1])
            p=[[px-cx,py-cy] for px,py in hexpts(cx,cy)]
            if dh<46 and random.random()<0.92:
                el("line",cx,cy,2*R,2*R,stroke="#495057",bg="#868e96",fill="solid",sw=1.6,extra={"points":p+[p[0]],"startBinding":None,"endBinding":None,"startArrowhead":None,"endArrowhead":None,"polygon":True}); claimed_centers.append((cx,cy))
            elif dh<92 and random.random()<0.85:
                el("line",cx,cy,2*R,2*R,stroke="#6b7178",bg="#b9bec4",fill="solid",sw=1.3,extra={"points":p+[p[0]],"startBinding":None,"endBinding":None,"startArrowhead":None,"endArrowhead":None,"polygon":True}); claimed_centers.append((cx,cy))
            elif dr<54 and random.random()<0.85:
                el("line",cx,cy,2*R,2*R,stroke="#adb5bd",bg="#dfe3e7",fill="solid",sw=1.2,extra={"points":p+[p[0]],"startBinding":None,"endBinding":None,"startArrowhead":None,"endArrowhead":None,"polygon":True})
            else:
                el("line",cx,cy,2*R,2*R,stroke="#e3e3e3",bg="#fbfbfb",fill="solid",sw=1,extra={"points":p+[p[0]],"startBinding":None,"endBinding":None,"startArrowhead":None,"endArrowhead":None,"polygon":True})
        c+=1; cx+=dxh
    r+=1; cy+=dyh
# route through some claimed cells
if len(claimed_centers)>6:
    pick=sorted(random.sample(claimed_centers,6),key=lambda p:p[0])
    ox,oy=pick[0]; line(ox,oy,[[px-ox,py-oy] for px,py in pick],stroke="#495057",sw=2.5)
# float chip
rect(mc_x+16,mc_y+mc_h-46,150,32,stroke=GREY,bg=WHITE,round_=R3); text(mc_x+30,mc_y+mc_h-39,"142 hexes held",T_SM,DARK)

# Weekly chart card
wc_x,wc_y,wc_w,wc_h=IX,GT+344,LCW,236
card(wc_x,wc_y,wc_w,wc_h)
text(wc_x+20,wc_y+16,"Weekly volume",T_SUB,DARK); text(wc_x+wc_w-90,wc_y+18,"Distance",T_CAP,GREY)
base=wc_y+wc_h-34; vals=[34,62,8,48,30,100,54]; labels=["M","T","W","T","F","S","S"]
n=len(vals); bw=40; gap=(wc_w-80-n*bw)/(n-1)
for i,v in enumerate(vals):
    bx=wc_x+40+i*(bw+gap); bh=int((wc_h-110)*v/100)
    rect(bx,base-bh,bw,bh,stroke=GREY,bg=(GREY if v==100 else BAR),round_=R3); ctext(bx+bw/2,base+10,labels[i],T_CAP,GREY)

# Goals card (right)
gc_x,gc_y,gc_w,gc_h=RCX,GT,RCW,200
card(gc_x,gc_y,gc_w,gc_h)
text(gc_x+20,gc_y+16,"Weekly goal",T_SUB,DARK)
def goalbar(gy,label,frac,note):
    text(gc_x+20,gy,label,T_SM,DARK); text(gc_x+gc_w-80,gy,note,T_CAP,GREY)
    rect(gc_x+20,gy+22,gc_w-40,12,stroke=BAR,bg=BAR,round_=R3); rect(gc_x+20,gy+22,int((gc_w-40)*frac),12,stroke=GREY,bg=GREY,round_=R3)
goalbar(gc_y+58,"Hexes",1.0,"10 / 10 ✓")
goalbar(gc_y+118,"5 runs",0.6,"3 / 5")

# Leaderboard card (right)
lc_x,lc_y,lc_w,lc_h=RCX,GT+224,RCW,356
card(lc_x,lc_y,lc_w,lc_h)
text(lc_x+20,lc_y+16,"Local leaderboard",T_SUB,DARK); text(lc_x+lc_w-90,lc_y+18,"Hackney",T_CAP,GREY)
hline(lc_x,lc_y+48,lc_w,stroke=LINE)
def lbrow(ry,rank,initials,name,score,me=False):
    if me: rect(lc_x+10,ry-6,lc_w-20,48,stroke=CARD,bg="#eef0f2",round_=R3)
    text(lc_x+22,ry+10,rank,T_BODY,GREY)
    ellipse(lc_x+44,ry+4,34,34,stroke=GREY,bg=WHITE); ctext(lc_x+61,ry+21,initials,T_CAP,GREY)
    text(lc_x+92,ry+10,name,T_BODY,DARK); text(lc_x+lc_w-58,ry+8,score,T_SUB,DARK)
ry=lc_y+66
for rk,ini,nm,sc,me in [("1","AK","Aoife Kelly","156",False),("2","MO","Marcus O.","148",False),
                        ("3","T","You","142",True),("4","PS","Priya S.","131",False)]:
    lbrow(ry,rk,ini,nm,sc,me); ry+=68

# ---------- recent activities table ----------
ty=GT+584
ta_x,ta_y,ta_w,ta_h=IX,ty,IW,260
card(ta_x,ta_y,ta_w,ta_h)
text(ta_x+20,ta_y+16,"Recent activities",T_SUB,DARK); text(ta_x+ta_w-80,ta_y+18,"View all",T_CAP,GREY)
cols=["Activity","Date","Distance","Pace","Time","Hexes"]; colw=[360,200,170,170,170,140]
hx=ta_x+24; hy=ta_y+52
rect(ta_x+16,hy,ta_w-32,34,stroke=CARD,bg="#f1f3f5",round_=R3)
cx=hx
for i,c in enumerate(cols): text(cx,hy+9,c,T_SM,DARK); cx+=colw[i]
rows=[["Riverside loop","Today 7:12","8.4 km","4:53/km","41:03","+6"],
      ["Park sprints","Tue 18:40","5.1 km","5:09/km","26:18","+3"],
      ["Long Sunday","Sun 9:05","16.2 km","5:11/km","1:24:09","+9"],
      ["Commute dash","Fri 7:30","4.0 km","4:58/km","19:55","+2"]]
ry=hy+44
for rrow in rows:
    cx=hx
    for i,c in enumerate(rrow):
        text(cx,ry+8,c,T_SM,DARK if i==0 else GREY); cx+=colw[i]
    hline(ta_x+16,ry+34,ta_w-32,stroke=LINE); ry+=42
CUR[0]=None

scene={"type":"excalidraw","version":2,"source":"https://excalidraw.com",
       "elements":els,"appState":{"gridSize":None,"viewBackgroundColor":"#ffffff"},"files":{}}
with open("hexagone-dashboard-example.excalidraw","w") as f:
    json.dump(scene,f)
print("elements:",len(els))
