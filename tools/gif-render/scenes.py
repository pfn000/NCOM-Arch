
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
    """Saidie 4:03 PM Oct 18: the window does NOT shrink while dragging; only the arc
    moves slightly with the finger; release = a quick inward flick and the window closes away."""
    T=2.45; fr=base(); dock(fr)
    c=geo_ctrl(G0); a=c['arc']; start=(a[0]+60,a[1]+90)
    dvec=(-0.82,0.57)                      # inward: from the top-right corner toward the window's middle
    st={}; al=1; fing=None; g=G0
    def nudge(dist): return (dvec[0]*min(dist,6)*0.9,dvec[1]*min(dist,6)*0.9)
    if t<0.8:
        pos=move(start,a,seg(t,0.15,0.62)); p=seg(t,0.62,0.78)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p); st['arc_on']=p>0.3
    elif t<1.3:                            # slow drag: arc follows a few px, window stays put, full size
        dist=14*ease(seg(t,0.8,1.3)); st.update(arc_on=True,arc_off=nudge(dist*0.4))
        fing=dict(x=a[0]+dvec[0]*dist,y=a[1]+dvec[1]*dist,p=1)
    elif t<1.42:                           # flick
        q=seg(t,1.3,1.42); dist=14+40*q*q; st.update(arc_on=True,arc_off=nudge(6))
        fing=dict(x=a[0]+dvec[0]*dist,y=a[1]+dvec[1]*dist,p=1-q,a=1-0.6*q)
    elif t<1.74:                           # closes away inward, ease-in, ~320 ms
        q=seg(t,1.42,1.74); e=q*q*q; off=150*e
        g=(G0[0]+dvec[0]*off,G0[1]+dvec[1]*off,G0[2],G0[3]); al=1-e
        st.update(arc_on=True,arc_off=nudge(6))
        dist=54; fing=dict(x=a[0]+dvec[0]*dist,y=a[1]+dvec[1]*dist,p=0,a=0.4*(1-seg(t,1.42,1.6)))
    elif t<2.7:
        al=0
    else:                                  # back for the loop
        q=eout(seg(t,2.7,3.2)); al=q; g=(G0[0],G0[1]+8*(1-q),G0[2],G0[3])
    if al>0.001:
        if al>=0.999 and g==G0: render_window(fr,g,st)
        else: render_window(fr,g,st,k=1.0,alpha=al,origin=(g[0]+g[2]/2,g[1]+g[3]/2))
    finger(fr,fing)
    caption(fr,'Flick the corner arc inward → CLOSE')
    return fr,T

CHIP=(385,333,96,32)
def pill_minimize(t):
    T=2.45; fr=base()
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
    elif t<99:
        draw=False; chip=dict(a=1)
    elif t<2.65:
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
    caption(fr,'Swipe pill down → MINIMIZE')
    return fr,T

GMAX=(8,48,584,276)
def pill_maximize(t):
    T=2.3; fr=base(); dock(fr)
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
    elif t<99:
        g=GMAX
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
    caption(fr,'Swipe pill up → MAXIMIZE')
    return fr,T

def zoom_frame(fr,box,z):
    """camera push-in: z=0 full frame, z=1 crops to box (1x px coords, 600x375 aspect) and fills the frame"""
    if z<=0.001: return fr
    x0,y0,x1,y1=[lerp(f,t,z) for f,t in zip((0,0,W,H),box)]
    return fr.crop((int(x0*S),int(y0*S),int(x1*S),int(y1*S))).resize((CW,CH),Image.LANCZOS)

PI_ZOOM=None
def pill_info_zoom_box():
    # Properties + quick settings region of the popover (anchor = pill corner), padded to the frame's 16:10 aspect
    x1=G0[0]+G0[2]-8; x0=x1-246; y0=G0[1]+20
    cx=(x0+x1)/2; cy=y0+136; h=178; w=h*W/H
    return (cx-w/2,cy-h/2,cx+w/2,cy+h/2)

def pill_info(t):
    # 0-1.2 tap pill, popover opens; 1.45-1.95 camera pushes in on Properties so size/path/toggles read on a phone;
    # hold to 3.75; 3.75-4.25 back out; hold the open popover to the end
    T=4.9; fr=base(); dock(fr)
    pl=geo_ctrl(G0)['pill']; start=(pl[0]+60,pl[1]+120); st={}; fing=None; pop=0
    if t<1.2:
        pos=move(start,pl,seg(t,0.15,0.6)); p=seg(t,0.62,0.72)*(1-seg(t,0.78,0.88))
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35)*(1-seg(t,1.0,1.2)),p=p,ripple=seg(t,0.75,1.05) if t>0.75 else None)
        st.update(pill_on=0.62<t<0.95,pill_w=28+4*p); pop=seg(t,0.78,1.12)
    else:
        pop=1
    st['pill_on']=st.get('pill_on') or pop>0.5
    render_window(fr,G0,st)
    popover(fr,G0[0]+G0[2]-8,G0[1]+20,pop)
    finger(fr,fing)
    z=ease(seg(t,1.45,1.95))*(1-ease(seg(t,3.75,4.25)))
    fr=zoom_frame(fr,pill_info_zoom_box(),z)
    caption(fr,'Tap pill → INFO / PROPERTIES')
    return fr,T

# ---------------- ••• app menu / settings (Saidie 4:06 PM Oct 18: "it's actually the actual settings") ----------------
GM=(95,56,410,232)
MENU_ROWS=[('chips',None),('sep',None),
 ('item','About Programming',''),('item','Settings…','⌘,'),('item','Keyboard Shortcuts','⌘/'),('item','Help & Feedback',''),('sep',None),
 ('toggle','Keep on Top',''),('sub','Snap Layout',''),('sub','Glass',''),('sub','Move to Desktop',''),('sep',None),
 ('sub','Notifications',''),('sub','Appearance',''),('item','Reset App…',''),('sep',None),
 ('item','Hide Programming','⌘H'),('item','Quit Programming','⌘Q')]
MW=204; RH=14.5; SEPH=6; CHH=20; MPAD=5
MENU_GAP=12   # menu top sits this far BELOW the ••• handle, so the handle is never covered (Saidie 5:31 PM Oct 14)
def menu_top(g): return geo_ctrl(g)['dots'][1]+MENU_GAP
def menu_layout(top):
    y=top+MPAD; out=[]
    for kind,*rest in MENU_ROWS:
        h=CHH if kind=='chips' else SEPH if kind=='sep' else RH
        out.append((kind,rest,y,h)); y+=h
    return out,y+MPAD
def menu_row_y(label,top):
    for kind,rest,y,h in menu_layout(top)[0]:
        if rest and rest[0]==label: return y+h/2
def app_menu(frame,cx,top,p,hi_y=None,toggle_on=0.0):
    if p<=0.01: return
    rows,bot=menu_layout(top); x0=cx-MW/2; x1=cx+MW/2
    lay=Image.new('RGBA',(CW,CH),(0,0,0,0))
    glass_refract(lay,[x0*S,top*S,x1*S,bot*S],14*S,tint=0.72,blur=6,bend=12,band=16,shadow_s=0.22,backdrop=frame.convert('RGB'))
    ov=Image.new('RGBA',(CW,CH),(0,0,0,0)); d=ImageDraw.Draw(ov)
    f=font(9.5,'SemiBold'); fs=font(8,'Medium'); fc=font(9,'SemiBold')
    if hi_y is not None:
        cands=[y+h/2 for kind,rest,y,h in rows if kind in ('item','sub','toggle')]
        hi_y=min(cands,key=lambda v:abs(v-hi_y))
        d.rounded_rectangle([(x0+5)*S,(hi_y-RH/2+0.5)*S,(x1-5)*S,(hi_y+RH/2-0.5)*S],radius=6*S,fill=(70,76,86,70))
    for kind,rest,y,h in rows:
        if kind=='sep':
            d.line([((x0+10)*S,(y+h/2)*S),((x1-10)*S,(y+h/2)*S)],fill=(120,126,136,110),width=max(1,S//2)); continue
        if kind=='chips':   # program menus kept as a quiet secondary row; the settings groups below are the focus
            labels=['File','Edit','View']; fcs=font(8,'Medium'); cw=(MW-12-2*4)/3
            for i,l in enumerate(labels):
                bx=x0+6+i*(cw+4)
                d.rounded_rectangle([bx*S,(y+3)*S,(bx+cw)*S,(y+h-3)*S],radius=7*S,fill=(255,255,255,40),outline=(150,156,166,90),width=max(1,S//2))
                tw=fcs.getlength(l)/S; d.text(((bx+cw/2-tw/2)*S,(y+5)*S),l,font=fcs,fill=TXT2)
            continue
        label,sc_=rest[0],rest[1]
        ty=y+(h-11.5)/2
        d.text(((x0+14)*S,ty*S),label,font=f,fill=TXT)
        if kind=='item' and sc_:
            tw=fs.getlength(sc_)/S; d.text(((x1-12-tw)*S,(ty+1)*S),sc_,font=fs,fill=TXT2)
        if kind=='sub':
            d.text(((x1-16)*S,(ty-1.5)*S),'›',font=font(11,'Medium'),fill=TXT2)
        if kind=='toggle':
            tx1=x1-12; tx0=tx1-22; tyc=y+h/2; k=toggle_on
            col=tuple(int(lerp(a,b,k)) for a,b in zip((196,200,206),(40,46,56)))
            d.rounded_rectangle([tx0*S,(tyc-6)*S,tx1*S,(tyc+6)*S],radius=6*S,fill=col+(255,))
            kx=lerp(tx0+6,tx1-6,k); d.ellipse([(kx-4.6)*S,(tyc-4.6)*S,(kx+4.6)*S,(tyc+4.6)*S],fill=(255,255,255,255))
    lay.alpha_composite(ov)
    frame.alpha_composite(scale_layer(lay,lerp(0.6,1,eout(p)),cx,top-6,alpha=clamp(p*1.6)))

def dots_menu(t):
    T=3.5; fr=base(); dock(fr)
    dt=geo_ctrl(GM)['dots']; start=(dt[0]+40,dt[1]+140); st={}; fing=None; mp=0; hi=None; tog=0
    top=menu_top(GM)
    yS=menu_row_y('Settings…',top); yG=menu_row_y('Glass',top); yK=menu_row_y('Keep on Top',top); mx=dt[0]-30
    if t<1.1:
        pos=move(start,dt,seg(t,0.15,0.6)); p=seg(t,0.62,0.72)*(1-seg(t,0.78,0.88))
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p,ripple=seg(t,0.75,1.05) if t>0.75 else None)
        st.update(dots_on=0.6<t<0.9); mp=seg(t,0.8,1.1)
    elif t<2.6:   # press and slide down through the menu: the highlight follows the finger
        mp=1; q=seg(t,1.25,2.3)
        pos=move(dt,(mx,yS),seg(t,1.1,1.3)) if t<1.3 else (mx,lerp(yS,yG,ease(q)) if q<0.6 else lerp(yG,yK,ease((q-0.6)/0.4)))
        if isinstance(pos,tuple) and len(pos)==2: fx,fy=pos
        pr=seg(t,1.22,1.3)
        if t>=1.3:
            fy=lerp(yS,yG,ease(seg(t,1.3,1.9))) if t<1.9 else lerp(yG,yK,ease(seg(t,1.95,2.35)))
            fx=mx
        fing=dict(x=fx,y=fy,p=pr*(1-seg(t,2.42,2.5)))
        if t>=1.3: hi=fy
        tog=ease(seg(t,2.45,2.6))
        if t>2.45: fing['ripple']=seg(t,2.45,2.7)
    else:
        mp=1; tog=1; hi=yK
        fing=dict(x=mx,y=yK,p=0,a=1-seg(t,2.6,2.85))
    if mp>0.05: st.update(dots_on=True,dots_held=True)   # ••• stays visible, shown as the active control
    render_window(fr,GM,st)
    app_menu(fr,dt[0],top,mp,hi_y=hi,toggle_on=tog)
    finger(fr,fing)
    caption(fr,'Tap ••• → APP MENU / SETTINGS')
    return fr,T

def settings_sheet(frame,g,p,tog=0.0):
    if p<=0.01: return
    x,y,w,h=g; x0=x+14; y0=y+24; x1=x+w-14; y1=y+h-14
    lay=Image.new('RGBA',(CW,CH),(0,0,0,0))
    glass_refract(lay,[x0*S,y0*S,x1*S,y1*S],18*S,tint=0.84,blur=8,bend=12,band=16,shadow_s=0.2,shadow_blur=14,shadow_dy=8,backdrop=frame.convert('RGB'))
    d=ImageDraw.Draw(lay); f=font(9.5,'Medium'); fb=font(11.5,'SemiBold'); fs=font(8.5,'Medium')
    side=['General','Appearance','Window','Notifications','Permissions','Language','Shortcuts','About']
    sx=x0+10
    d.text((sx*S,(y0+9)*S),'Settings',font=font(10,'SemiBold'),fill=TXT2)
    for i,lbl in enumerate(side):
        yy=y0+26+i*18
        if yy+14>y1: break
        if i==0: d.rounded_rectangle([(sx-4)*S,(yy-2)*S,(sx+84)*S,(yy+14)*S],radius=6*S,fill=(70,76,86,60))
        d.text((sx*S,yy*S),lbl,font=f,fill=TXT)
    vx=x0+104; d.line([((vx-8)*S,(y0+10)*S),((vx-8)*S,(y1-10)*S)],fill=(120,126,136,90),width=max(1,S//2))
    d.text((vx*S,(y0+8)*S),'Programming · General',font=fb,fill=TXT)
    rx1=x1-14
    def row(i,label): 
        yy=y0+32+i*30; d.rounded_rectangle([vx*S,yy*S,rx1*S,(yy+24)*S],radius=9*S,fill=(255,255,255,175),outline=(255,255,255,210),width=S)
        d.text(((vx+10)*S,(yy+6.5)*S),label,font=f,fill=TXT); return yy
    def toggle(yy,k):
        tx1=rx1-10; tx0=tx1-24; tyc=yy+12
        col=tuple(int(lerp(a,b,k)) for a,b in zip((196,200,206),(40,46,56)))
        d.rounded_rectangle([tx0*S,(tyc-6.5)*S,tx1*S,(tyc+6.5)*S],radius=6.5*S,fill=col+(255,))
        kx=lerp(tx0+6.5,tx1-6.5,k); d.ellipse([(kx-5)*S,(tyc-5)*S,(kx+5)*S,(tyc+5)*S],fill=(255,255,255,255))
    yy=row(0,'Open at login'); toggle(yy,1)
    yy=row(1,'Appearance')
    segs=['Light','Dark','Auto']; sw=34; sx0=rx1-10-sw*3
    d.rounded_rectangle([sx0*S,(yy+4)*S,(rx1-10)*S,(yy+20)*S],radius=8*S,fill=(200,204,210,140))
    for j,sg in enumerate(segs):
        if j==2: d.rounded_rectangle([(sx0+j*sw+1)*S,(yy+5)*S,(sx0+(j+1)*sw-1)*S,(yy+19)*S],radius=7*S,fill=(255,255,255,235))
        tw=fs.getlength(sg)/S; d.text(((sx0+j*sw+sw/2-tw/2)*S,(yy+6.5)*S),sg,font=fs,fill=TXT)
    yy=row(2,'Glass')
    gx0=rx1-110; gx1=rx1-12; gy=yy+12
    d.text(((gx0-30)*S,(yy+7)*S),'Clear',font=fs,fill=TXT2)
    d.rounded_rectangle([gx0*S,(gy-2)*S,gx1*S,(gy+2)*S],radius=2*S,fill=(160,166,175,255))
    kx=lerp(gx0,gx1,0.35); d.rounded_rectangle([gx0*S,(gy-2)*S,kx*S,(gy+2)*S],radius=2*S,fill=(40,46,56,255))
    d.ellipse([(kx-6)*S,(gy-6)*S,(kx+6)*S,(gy+6)*S],fill=(255,255,255,255),outline=(150,156,166,255),width=S)
    yy=row(3,'Keep window on top'); toggle(yy,tog)
    yy=row(4,'Notifications'); d.text(((rx1-46)*S,(yy+7)*S),'Allowed  ›',font=fs,fill=TXT2)
    frame.alpha_composite(scale_layer(lay,lerp(0.94,1,eout(p)),x+w/2,y+h/2,alpha=clamp(p*1.4)))

def settings_toggle_y(g): return g[1]+24+32+3*30+12
def settings_toggle_x(g): return g[0]+g[2]-14-14-12

def dots_settings(t):
    T=3.7; fr=base(); dock(fr)
    dt=geo_ctrl(GM)['dots']; start=(dt[0]+40,dt[1]+140); st={}; fing=None; mp=0; hi=None; sp_=0; tog=0
    top=menu_top(GM); yS=menu_row_y('Settings…',top); mx=dt[0]-30
    if t<1.0:
        pos=move(start,dt,seg(t,0.15,0.55)); p=seg(t,0.55,0.63)*(1-seg(t,0.68,0.76))
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.3),p=p,ripple=seg(t,0.66,0.95) if t>0.66 else None)
        st.update(dots_on=0.55<t<0.8); mp=seg(t,0.7,0.98)
    elif t<1.75:
        mp=1; pos=move(dt,(mx,yS),seg(t,1.0,1.4)); pr=seg(t,1.45,1.52)*(1-seg(t,1.58,1.66))
        fing=dict(x=pos[0],y=pos[1],p=pr,ripple=seg(t,1.55,1.85) if t>1.55 else None)
        if t>1.38: hi=yS
    else:
        mp=1-seg(t,1.75,1.95); hi=yS if mp>0 else None; sp_=seg(t,1.85,2.2)
        tx,ty=settings_toggle_x(GM),settings_toggle_y(GM)
        pos=move((mx,yS),(tx,ty),seg(t,2.25,2.7)); pr=seg(t,2.72,2.8)*(1-seg(t,2.84,2.92))
        fing=dict(x=pos[0],y=pos[1],p=pr,a=1-seg(t,3.05,3.3),ripple=seg(t,2.8,3.05) if 2.8<t<3.05 else None)
        tog=ease(seg(t,2.8,2.95))
    if max(mp,sp_)>0.05: st.update(dots_on=True,dots_held=mp>0.05)
    st['content_alpha']=1-0.85*sp_
    render_window(fr,GM,st)
    settings_sheet(fr,GM,sp_,tog=tog)
    app_menu(fr,dt[0],top,mp,hi_y=hi)
    finger(fr,fing)
    caption(fr,'Tap Settings… → SETTINGS SHEET')
    return fr,T


def dots_move(t):
    T=2.85; fr=base(); dock(fr)
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
    elif t<99:
        q=1; lift=0; d1=geo_ctrl(gat(1))['dots']
        fing=dict(x=d1[0],y=d1[1],p=0,a=1-seg(t,2.2,2.45))
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
    caption(fr,'Hold ••• → MOVE')
    return fr,T

GLH=(8,48,288,276)
def snap_preview(fr,g,a):
    if a<=0.01: return
    x,y,w,h=g; lay=Image.new('RGBA',(CW,CH),(0,0,0,0))
    glass(lay,[x*S,y*S,(x+w)*S,(y+h)*S],24*S,tint=0.55,blur=10,edge=False,shadow_s=0,backdrop=fr.convert('RGB'))
    d=ImageDraw.Draw(lay); d.rounded_rectangle([x*S,y*S,(x+w)*S,(y+h)*S],radius=24*S,outline=(255,255,255,235),width=int(2*S))
    d.rounded_rectangle([(x+3)*S,(y+3)*S,(x+w-3)*S,(y+h-3)*S],radius=21*S,outline=(90,96,106,120),width=S)
    lay.putalpha(lay.getchannel('A').point(lambda v:int(v*a)))
    fr.alpha_composite(lay)

def dots_snap(t):
    T=3.7; fr=base(); dock(fr)
    st={}; fing=None; lift=0; prev=None; pa=0
    d0=geo_ctrl(G0)['dots']; top_pt=(300,46)
    def at(fx,fy,w=G0[2],h=G0[3]): return (fx-w/2,fy-7,w,h)
    if t<0.6:
        pos=move((d0[0]+40,d0[1]+120),d0,seg(t,0.1,0.4)); p=seg(t,0.4,0.5)
        g=G0; lift=seg(t,0.45,0.6); st.update(dots_on=p>0.3,dots_held=t>0.45)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.05,0.25),p=p)
    elif t<1.25:                         # drag up to the top edge
        q=ease(seg(t,0.6,1.05)); fx,fy=lerp(d0[0],top_pt[0],q),lerp(d0[1],top_pt[1],q)
        g=at(fx,fy); lift=1; st.update(dots_on=True,dots_held=True)
        fing=dict(x=fx,y=fy,p=1); prev=GMAX; pa=seg(t,0.98,1.12)
    elif t<1.9:                          # release: fills the screen
        q=ease(seg(t,1.25,1.55)); g0=at(*top_pt)
        g=tuple(lerp(g0[i],GMAX[i],q) for i in range(4)); lift=1-q
        prev=GMAX; pa=1-seg(t,1.3,1.5)
        fing=dict(x=top_pt[0],y=top_pt[1],p=1-seg(t,1.25,1.32),a=1-seg(t,1.35,1.6))
    elif t<2.75:                         # grab ••• again and drag to the left edge
        dm=geo_ctrl(GMAX)['dots']; left_pt=(10,112)
        if t<2.15:
            pos=move((dm[0]+50,dm[1]+110),dm,seg(t,1.9,2.08)); p=seg(t,2.08,2.15)
            g=GMAX; st.update(dots_on=p>0.3,dots_held=t>2.1); lift=seg(t,2.1,2.15)
            fing=dict(x=pos[0],y=pos[1],a=seg(t,1.9,2.0),p=p)
        else:
            q=ease(seg(t,2.15,2.6)); fx,fy=lerp(dm[0],left_pt[0],q),lerp(dm[1],left_pt[1],q)
            k=ease(seg(t,2.15,2.35)); w=lerp(GMAX[2],G0[2],k); h=lerp(GMAX[3],G0[3],k)
            g=at(fx,fy,w,h); lift=1; st.update(dots_on=True,dots_held=True)
            fing=dict(x=fx,y=fy,p=1); prev=GLH; pa=seg(t,2.5,2.62)
    else:                                # release: snaps to the left half
        left_pt=(10,112); q=ease(seg(t,2.75,3.05)); g0=at(*left_pt)
        g=tuple(lerp(g0[i],GLH[i],q) for i in range(4)); lift=1-q
        prev=GLH; pa=1-seg(t,2.8,3.0)
        fing=dict(x=left_pt[0],y=left_pt[1],p=1-seg(t,2.75,2.82),a=1-seg(t,2.85,3.1))
    snap_preview(fr,prev,pa) if prev else None
    st['lift']=lift
    render_window(fr,g,st,k=1+0.02*lift)
    finger(fr,fing)
    caption(fr,'Hold ••• + drag to an edge → SNAP')
    return fr,T

GR=(95,64,360,196)
def resize(t):
    T=2.95; fr=base(); dock(fr)
    D=(95,56); st={}; fing=None; q=0; ha=0
    def gat(q): return (GR[0],GR[1],GR[2]+D[0]*q,GR[3]+D[1]*q)
    c0=geo_ctrl(GR)['corner']
    if t<0.95:
        pos=move((c0[0]+70,c0[1]+50),c0,seg(t,0.15,0.65)); ha=seg(t,0.5,0.8); p=seg(t,0.8,0.95)
        fing=dict(x=pos[0],y=pos[1],a=seg(t,0.1,0.35),p=p); st['handle_on']=p>0.4
    elif t<2.0:
        q=ease(seg(t,0.95,1.8)); ha=1; st['handle_on']=t<1.85
        fing=dict(x=c0[0]+D[0]*q,y=c0[1]+D[1]*q,p=1-seg(t,1.85,1.95))
    else:
        q=1; ha=1-seg(t,2.05,2.3); c1=geo_ctrl(gat(1))['corner']
        fing=dict(x=c1[0]+30*seg(t,2.0,2.4),y=c1[1]+20*seg(t,2.0,2.4),p=0,a=1-seg(t,2.05,2.35))
    st['handle_alpha']=ha
    render_window(fr,gat(q),st)
    if q>0.02:   # dashed outline of the old size, so the change in size is unmistakable
        ov=Image.new('RGBA',(CW,CH),(0,0,0,0)); d=ImageDraw.Draw(ov); A=int(170*min(1,q*3))
        x0,y0,x1,y1=GR[0]*S,GR[1]*S,(GR[0]+GR[2])*S,(GR[1]+GR[3])*S
        for xx in range(int(x0+24*S),int(x1-24*S),int(10*S)):
            d.line([(xx,y1),(min(xx+5*S,x1-24*S),y1)],fill=(60,66,76,A),width=int(1.5*S))
        for yy in range(int(y0+24*S),int(y1-24*S),int(10*S)):
            d.line([(x1,yy),(x1,min(yy+5*S,y1-24*S))],fill=(60,66,76,A),width=int(1.5*S))
        d.arc([x1-48*S,y1-48*S,x1,y1],0,90,fill=(60,66,76,A),width=int(1.5*S))
        g=gat(q); wtxt=f"{int(round(g[2]))} × {int(round(g[3]))}"
        fz=font(9.5,'SemiBold'); tw=fz.getlength(wtxt)
        lx=(g[0]+g[2])*S-tw-20*S; ly=(g[1]+g[3])*S+6*S
        d.rounded_rectangle([lx-6*S,ly,lx+tw+6*S,ly+16*S],radius=8*S,fill=(40,46,56,int(200*min(1,q*3))))
        d.text((lx,ly+2.5*S),wtxt,font=fz,fill=(250,251,252,int(255*min(1,q*3))))
        fr.alpha_composite(ov)
    finger(fr,fing)
    caption(fr,'Drag hidden corner → RESIZE','The handle only shows while you resize')
    return fr,T

def bubble(t):
    T=3.0; fr=base(); dock(fr)
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
    caption(fr,'Can\'t resize → BOUNCE','This window doesn\'t resize, so the corner springs back')
    return fr,T

SCENES=dict(arc_close=arc_close,pill_minimize=pill_minimize,pill_maximize=pill_maximize,pill_info=pill_info,dots_menu=dots_menu,dots_move=dots_move,dots_settings=dots_settings,dots_snap=dots_snap,resize=resize,bubble=bubble)
if __name__=='__main__':
    name=sys.argv[1]; out=sys.argv[2]; mode=sys.argv[3] if len(sys.argv)>3 else 'gif'
    fn=SCENES[name]; _,T=fn(0)
    if mode.startswith('still'):
        ts=[float(v) for v in mode.split(':')[1].split(',')]
        ims=[fn(t)[0].convert('RGB').resize((W,H),Image.LANCZOS) for t in ts]
        sheet=Image.new('RGB',(W*len(ims),H)); [sheet.paste(im,(i*W,0)) for i,im in enumerate(ims)]
        sheet.save(out,quality=88); sys.exit(0)
    TT=min(T,{'pill_info':5.0}.get(name,4.0)); n=int(round(TT*FPS)); frames=[]   # 04 keeps real time for its zoom beat
    for i in range(n):
        frames.append(fn(i/FPS*T/TT)[0].convert('RGB').resize((W,H),Image.LANCZOS))
    save_gif(frames,out)
