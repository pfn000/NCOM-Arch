
import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from ncom_core import *

G0=(95,64,410,232)
def geo_ctrl(g):
    x,y,w,h=g
    return dict(arc=(x+w-24+12,y+24-12), pill=(x+w-54,y+7), dots=(x+w/2,y+7), corner=(x+w-9,y+h-9))

def render_window(frame,g,st,k=1.0,alpha=1.0,warp=None,origin=None):
    st=dict(st)
    if k==1.0 and alpha>=0.999 and warp is None:
        st['backdrop']=frame.convert('RGB'); window_layer(frame,g,st); return
    lay=Image.new('RGBA',(CW,CH),(0,0,0,0)); st['backdrop']=frame.convert('RGB')
    window_layer(lay,g,st)
    if warp: lay=warp_layer(lay,*warp)
    ox,oy=origin if origin else (g[0]+g[2]/2,g[1]+g[3]/2)
    frame.alpha_composite(scale_layer(lay,k,ox,oy,alpha))

def base():
    return BG.convert('RGBA')

def move(p0,p1,x): x=ease(x); return (lerp(p0[0],p1[0],x),lerp(p0[1],p1[1],x))

# ---------------- scenes ----------------
def arc_close(t):
    T=3.4; fr=base(); dock(fr)
    c=geo_ctrl(G0); a=c['arc']; start=(a[0]+60,a[1]+90)
    st={}; k=1; al=1; fing=None; g=G0
    drag=(-70,46)
    def gd(q): return (G0[0],G0[1]+drag[1]*q,G0[2]+drag[0]*q,G0[3]-drag[1]*q)
    if t<0.85:
        pos=move(start,a,seg(t,0.15,0.7)); p=seg(t,0.7,0.85)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p); st['arc_on']=p>0.3
    elif t<1.65:
        q=ease(seg(t,0.85,1.6)); g=gd(q)
        st.update(arc_on=True,content_alpha=1-0.45*q)
        fing=dict(x=a[0]+drag[0]*q,y=a[1]+drag[1]*q,p=1)
    elif t<2.05:
        q=eout(seg(t,1.65,2.0)); g=gd(1); st.update(arc_on=True,content_alpha=0.55); k=1-0.2*q; al=1-q
        fing=dict(x=a[0]+drag[0],y=a[1]+drag[1],p=1-seg(t,1.65,1.75),a=1-seg(t,1.7,1.95))
    elif t<2.6:
        al=0
    else:
        q=eout(seg(t,2.6,3.15)); k=0.92+0.08*q; al=q
    if al>0.001: render_window(fr,g,st,k=k,alpha=al)
    finger(fr,fing)
    caption(fr,'Drag the corner arc  →  Close')
    return fr,T

CHIP=(385,333,96,32)
def pill_minimize(t):
    T=3.8; fr=base()
    c=geo_ctrl(G0); pl=c['pill']; start=(pl[0]+70,pl[1]+110)
    chip=None; st={}; fing=None; g=G0; draw=True
    if t<0.8:
        pos=move(start,pl,seg(t,0.15,0.65)); p=seg(t,0.65,0.8)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p); st.update(pill_on=p>0.3,pill_w=28+4*p)
    elif t<1.3:
        q=ease(seg(t,0.8,1.25)); dy=40*q
        g=(G0[0],G0[1]+dy*0.7,G0[2],G0[3]); st.update(pill_on=True,pill_w=32,pill_off=(0,dy*0.3))
        fing=dict(x=pl[0],y=pl[1]+dy,p=1)
    elif t<1.8:
        q=ease(seg(t,1.3,1.75)); g0=(G0[0],G0[1]+28,G0[2],G0[3])
        g=tuple(lerp(g0[i],CHIP[i],q) for i in range(4)); st.update(content_alpha=1-clamp(q*2.2),ctrl_alpha=1-clamp(q*2.5),r=min(24,g[3]/2))
        fing=dict(x=pl[0],y=pl[1]+40,p=1-seg(t,1.3,1.4),a=1-seg(t,1.35,1.6))
        if q>0.85: chip=dict(a=(q-0.85)/0.15); 
        if q>=0.999: draw=False
    elif t<2.65:
        draw=False; chip=dict(a=1)
        cc=(CHIP[0]+48,CHIP[1]+16)
        pos=move((cc[0]+60,cc[1]-90),cc,seg(t,1.95,2.4)); pr=seg(t,2.4,2.5)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,1.9,2.1),p=pr*(1-seg(t,2.5,2.6)),ripple=seg(t,2.48,2.65) if t>2.48 else None)
    elif t<3.2:
        q=ease(seg(t,2.65,3.15)); g=tuple(lerp(CHIP[i],G0[i],q) for i in range(4))
        st.update(content_alpha=clamp((q-0.4)/0.6),ctrl_alpha=clamp((q-0.5)/0.5),r=min(24,g[3]/2))
        chip=dict(a=1-clamp(q*4)) if q<0.25 else None
        cc=(CHIP[0]+48,CHIP[1]+16); fing=dict(x=cc[0],y=cc[1],a=1-seg(t,2.65,2.9))
    dock(fr,chip=chip)
    if draw: render_window(fr,g,st)
    finger(fr,fing)
    caption(fr,'Swipe the pill down  →  Minimize')
    return fr,T

GMAX=(8,48,584,276)
def pill_maximize(t):
    T=4.0; fr=base(); dock(fr)
    st={}; fing=None; g=G0
    pl=geo_ctrl(G0)['pill']; plm=geo_ctrl(GMAX)['pill']; start=(pl[0]+60,pl[1]+110)
    if t<0.8:
        pos=move(start,pl,seg(t,0.15,0.65)); p=seg(t,0.65,0.8)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p); st.update(pill_on=p>0.3,pill_w=28+4*p)
    elif t<1.15:
        q=ease(seg(t,0.8,1.1)); dy=-14*q
        st.update(pill_on=True,pill_w=32,pill_off=(0,dy*0.5)); g=(G0[0],G0[1]+dy*0.4,G0[2],G0[3])
        fing=dict(x=pl[0],y=pl[1]+dy,p=1)
    elif t<1.65:
        q=ease(seg(t,1.15,1.6)); g0=(G0[0],G0[1]-5.6,G0[2],G0[3])
        g=tuple(lerp(g0[i],GMAX[i],q) for i in range(4))
        fing=dict(x=pl[0],y=pl[1]-14,p=1-seg(t,1.15,1.25),a=1-seg(t,1.2,1.45))
    elif t<2.75:
        g=GMAX
        pos=move((plm[0]-80,plm[1]+120),plm,seg(t,2.0,2.45)); p=seg(t,2.45,2.6)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,1.95,2.15),p=p); st.update(pill_on=p>0.3,pill_w=28+4*p)
        if t>2.6:
            q=ease(seg(t,2.6,2.75)); st.update(pill_off=(0,10*q)); fing.update(y=plm[1]+28*q,p=1)
    elif t<3.3:
        q=ease(seg(t,2.75,3.25)); g=tuple(lerp(GMAX[i],G0[i],q) for i in range(4))
        fing=dict(x=plm[0],y=plm[1]+28,p=1-seg(t,2.75,2.85),a=1-seg(t,2.8,3.05))
    render_window(fr,g,st)
    finger(fr,fing)
    caption(fr,'Swipe the pill up  →  Maximize')
    return fr,T

def pill_info(t):
    T=3.8; fr=base(); dock(fr)
    pl=geo_ctrl(G0)['pill']; start=(pl[0]+60,pl[1]+120); st={}; fing=None; pop=0
    if t<1.2:
        pos=move(start,pl,seg(t,0.15,0.6)); p=seg(t,0.62,0.72)*(1-seg(t,0.78,0.88))
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35)*(1-seg(t,1.0,1.2)),p=p,ripple=seg(t,0.75,1.05) if t>0.75 else None)
        st.update(pill_on=0.62<t<0.95,pill_w=28+4*p); pop=seg(t,0.78,1.12)
    elif t<2.9:
        pop=1
        if t>2.3:
            tgt=(50,200); pos=move((tgt[0]+40,tgt[1]+70),tgt,seg(t,2.3,2.7)); p=seg(t,2.72,2.8)
            fing=dict(x=pos[0],y=pos[1],a=seg(t,2.3,2.45),p=p)
    else:
        pop=1-seg(t,2.95,3.2); tgt=(50,200)
        fing=dict(x=tgt[0],y=tgt[1],p=1-seg(t,2.9,3.0),a=1-seg(t,3.0,3.3),ripple=seg(t,2.9,3.2) if t<3.2 else None)
    st['pill_on']=st.get('pill_on') or pop>0.5
    render_window(fr,G0,st)
    popover(fr,G0[0]+G0[2]-8,G0[1]+20,pop)
    finger(fr,fing)
    caption(fr,'Tap the pill  →  Program info')
    return fr,T

def dots_menu(t):
    T=4.2; fr=base(); dock(fr)
    dt=geo_ctrl(G0)['dots']; start=(dt[0]+40,dt[1]+130); st={}; fing=None; mp=0; sel=None; drop=0
    mcx,mcy=dt[0],G0[1]+14
    f=font(10.5,'SemiBold'); items=['File','Edit','View']
    full=sum(f.getlength(x) for x in items)/S+3*24+12; filex=mcx-full/2+6+12+f.getlength('File')/S/2
    if t<1.4:
        pos=move(start,dt,seg(t,0.15,0.6)); p=seg(t,0.62,0.72)*(1-seg(t,0.78,0.88))
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p,ripple=seg(t,0.75,1.05) if t>0.75 else None)
        st.update(dots_on=0.6<t<0.9); mp=seg(t,0.8,1.15)
        if t>1.05: fing.update(x=dt[0],y=dt[1])
    elif t<3.1:
        mp=1
        pos=move(dt,(filex,mcy),seg(t,1.4,1.85)); p=seg(t,1.9,1.98)*(1-seg(t,2.02,2.1))
        fing=dict(x=pos[0],y=pos[1],p=p,ripple=seg(t,2.0,2.3) if 2.0<t<2.3 else None)
        if t>1.95: sel='File'; drop=seg(t,2.0,2.3)
        if t>2.7:
            tgt=(60,230); pos=move((filex,mcy),tgt,seg(t,2.7,3.05)); fing.update(x=pos[0],y=pos[1])
    else:
        tgt=(60,230); q=seg(t,3.15,3.45); sel='File'; drop=1-seg(t,3.15,3.35); mp=1-q
        if drop<=0: sel=None
        fing=dict(x=tgt[0],y=tgt[1],p=seg(t,3.1,3.15)*(1-seg(t,3.18,3.25)),a=1-seg(t,3.3,3.6),ripple=seg(t,3.15,3.45) if t<3.45 else None)
    st['dots_alpha']=1-clamp(mp*1.6)
    render_window(fr,G0,st)
    if mp>0.01: menubar(fr,mcx,mcy,mp,sel=sel,drop=drop)
    finger(fr,fing)
    caption(fr,'Tap •••  →  App menu (File · Edit · View)')
    return fr,T

def dots_move(t):
    T=4.4; fr=base(); dock(fr)
    OFF=(-62,26)
    def gat(q): return (G0[0]+OFF[0]*q,G0[1]+OFF[1]*q,G0[2],G0[3])
    st={}; fing=None; lift=0; q=0
    dt0=geo_ctrl(G0)['dots']
    if t<1.1:
        pos=move((dt0[0]+50,dt0[1]+130),dt0,seg(t,0.15,0.6)); p=seg(t,0.62,0.75)
        lift=seg(t,0.8,1.05); st.update(dots_on=p>0.3,dots_held=t>0.8)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p)
    elif t<2.2:
        q=ease(seg(t,1.1,2.0)); lift=1-seg(t,2.0,2.2); st.update(dots_on=True,dots_held=t<2.1)
        fing=dict(x=dt0[0]+OFF[0]*q,y=dt0[1]+OFF[1]*q,p=1-seg(t,2.0,2.1))
    elif t<3.3:
        q=1; d1=geo_ctrl(gat(1))['dots']; lift=seg(t,2.55,2.8)
        st.update(dots_on=t>2.4,dots_held=t>2.55)
        fing=dict(x=d1[0],y=d1[1],p=seg(t,2.4,2.5))
        if t>2.8:
            q=1-ease(seg(t,2.8,3.3)); fing.update(x=dt0[0]+OFF[0]*q,y=dt0[1]+OFF[1]*q,p=1)
    else:
        q=0; lift=1-seg(t,3.3,3.5); st.update(dots_on=t<3.45,dots_held=t<3.4)
        fing=dict(x=dt0[0],y=dt0[1],p=1-seg(t,3.35,3.45),a=1-seg(t,3.45,3.8))
    g=gat(q); st['lift']=lift
    render_window(fr,g,st,k=1+0.02*lift)
    finger(fr,fing)
    caption(fr,'Hold •••  →  Move the window')
    return fr,T

def resize(t):
    T=4.2; fr=base(); dock(fr)
    D=(42,24); st={}; fing=None; q=0; ha=0
    def gat(q): return (G0[0],G0[1],G0[2]+D[0]*q,G0[3]+D[1]*q)
    c0=geo_ctrl(G0)['corner']
    if t<0.95:
        pos=move((c0[0]+70,c0[1]+50),c0,seg(t,0.15,0.65)); ha=seg(t,0.5,0.8); p=seg(t,0.8,0.95)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p); st['handle_on']=p>0.4
    elif t<2.0:
        q=ease(seg(t,0.95,1.8)); ha=1; st['handle_on']=t<1.85
        fing=dict(x=c0[0]+D[0]*q,y=c0[1]+D[1]*q,p=1-seg(t,1.85,1.95))
    elif t<2.5:
        q=1; ha=1-seg(t,2.05,2.35); c1=geo_ctrl(gat(1))['corner']
        fing=dict(x=c1[0]+30*seg(t,2.0,2.4),y=c1[1]+20*seg(t,2.0,2.4),a=1-seg(t,2.05,2.35))
    elif t<3.6:
        c1=geo_ctrl(gat(1))['corner']
        pos=move((c1[0]+50,c1[1]+30),c1,seg(t,2.5,2.85)); ha=seg(t,2.65,2.85); p=seg(t,2.85,2.95)
        q=1-ease(seg(t,2.95,3.55)); st['handle_on']=t>2.88
        fing=dict(x=pos[0]-D[0]*(1-q),y=pos[1]-D[1]*(1-q),a=seg(t,2.5,2.65),p=p)
    else:
        q=0; ha=1-seg(t,3.65,3.95)
        fing=dict(x=c0[0],y=c0[1],p=1-seg(t,3.6,3.7),a=1-seg(t,3.65,3.95))
    st['handle_alpha']=ha
    render_window(fr,gat(q),st)
    finger(fr,fing)
    caption(fr,'Hidden corner  →  Resize','The handle only shows while you resize')
    return fr,T

def bubble(t):
    T=3.6; fr=base(); dock(fr)
    c0=geo_ctrl(G0)['corner']; corner=(G0[0]+G0[2],G0[1]+G0[3]); fing=None; disp=(0,0)
    DR=(44,30)
    if t<0.85:
        pos=move((c0[0]+70,c0[1]+50),c0,seg(t,0.15,0.65)); p=seg(t,0.7,0.85)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p)
    elif t<1.55:
        q=ease(seg(t,0.85,1.5)); fd=(DR[0]*q,DR[1]*q); r=0.5
        disp=(fd[0]*r,fd[1]*r); fing=dict(x=c0[0]+fd[0],y=c0[1]+fd[1],p=1)
    else:
        x=t-1.55; amp=math.exp(-4.2*x)*math.cos(2*math.pi*2.6*x)
        disp=(DR[0]*0.5*amp,DR[1]*0.5*amp)
        fing=dict(x=c0[0]+DR[0]+25*seg(t,1.55,1.9),y=c0[1]+DR[1]+15*seg(t,1.55,1.9),p=1-seg(t,1.55,1.62),a=1-seg(t,1.58,1.85))
    warp=(corner[0]-6,corner[1]-6,disp[0],disp[1],42) if abs(disp[0])+abs(disp[1])>0.2 else None
    render_window(fr,G0,{},warp=warp)
    finger(fr,fing)
    caption(fr,'Not resizable  →  Corner stretches & jiggles back')
    return fr,T

SCENES=dict(arc_close=arc_close,pill_minimize=pill_minimize,pill_maximize=pill_maximize,pill_info=pill_info,dots_menu=dots_menu,dots_move=dots_move,resize=resize,bubble=bubble)
if __name__=='__main__':
    name=sys.argv[1]; out=sys.argv[2]; mode=sys.argv[3] if len(sys.argv)>3 else 'gif'
    fn=SCENES[name]; _,T=fn(0)
    if mode.startswith('still'):
        ts=[float(v) for v in mode.split(':')[1].split(',')]
        ims=[fn(t)[0].convert('RGB').resize((W,H),Image.LANCZOS) for t in ts]
        sheet=Image.new('RGB',(W*len(ims),H)); [sheet.paste(im,(i*W,0)) for i,im in enumerate(ims)]
        sheet.save(out,quality=88); sys.exit(0)
    TT=min(T,4.0); n=int(round(TT*FPS)); frames=[]
    for i in range(n):
        frames.append(fn(i/FPS*T/TT)[0].convert('RGB').resize((W,H),Image.LANCZOS))
    save_gif(frames,out)
