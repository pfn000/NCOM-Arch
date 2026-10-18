
import sys, os, math, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

S=2; W,H=600,375; FPS=int(os.environ.get('NCOM_FPS','20'))
CW,CH=W*S,H*S
HERE=os.path.dirname(os.path.abspath(__file__))
FONT=os.environ.get('NCOM_FONT','/home/user/.local/share/fonts/Inter.ttf')  # Inter variable font
def font(sz,wt='Medium'):
    f=ImageFont.truetype(FONT,int(sz*S))
    try: f.set_variation_by_name(wt)
    except Exception: pass
    return f
CTRL=(88,94,104); ACT=(23,26,32); TXT=(23,26,32); TXT2=(81,89,101)
SKEL=(176,181,189)

def clamp(v,a=0.0,b=1.0): return max(a,min(b,v))
def seg(t,a,b): return clamp((t-a)/(b-a))
def ease(x): x=clamp(x); return 4*x*x*x if x<.5 else 1-pow(-2*x+2,3)/2
def eout(x): x=clamp(x); return 1-pow(1-x,3)
def lerp(a,b,x): return a+(b-a)*x
def spring(x,freq=3.0,damp=5.0):  # 0->1 overshoot settle
    x=max(0,x); return 1-math.exp(-damp*x)*math.cos(2*math.pi*freq*x)

# ---------- background ----------
def make_bg():
    y=np.linspace(0,1,CH)[:,None]; x=np.linspace(0,1,CW)[None,:]
    top=np.array([234,236,239]); bot=np.array([200,204,210])
    g=top[None,None,:]*(1-y[...,None])+bot[None,None,:]*y[...,None]
    g=g+0*x[...,None]
    im=Image.fromarray(g.astype(np.uint8),'RGB')
    blob=Image.new('L',(CW//4,CH//4),0); d=ImageDraw.Draw(blob)
    for (cx,cy,r,v) in [(.18,.30,.22,170),(.82,.72,.26,150),(.62,.12,.16,120),(.35,.85,.18,110)]:
        d.ellipse([(cx-r)*CW/4,(cy-r)*CW/4*0+cy*CH/4-r*CW/4,(cx+r)*CW/4,cy*CH/4+r*CW/4],fill=v)
    blob=blob.filter(ImageFilter.GaussianBlur(28)).resize((CW,CH),Image.BICUBIC)
    dark=Image.new('RGB',(CW,CH),(150,156,165))
    im=Image.composite(dark,im,blob.point(lambda p:int(p*0.55)))
    blob2=Image.new('L',(CW//4,CH//4),0); d=ImageDraw.Draw(blob2)
    d.ellipse([CW/4*.55,CH/4*.25,CW/4*.95,CH/4*1.05],fill=200); d.ellipse([CW/4*.0,CH/4*.55,CW/4*.3,CH/4*1.2],fill=160)
    blob2=blob2.filter(ImageFilter.GaussianBlur(30)).resize((CW,CH),Image.BICUBIC)
    im=Image.composite(Image.new('RGB',(CW,CH),(247,248,250)),im,blob2.point(lambda p:int(p*0.6)))
    return im
BG=make_bg()

def rr_mask(size,box,r):
    m=Image.new('L',size,0); ImageDraw.Draw(m).rounded_rectangle(box,radius=r,fill=255); return m

def shadow(frame,box,r,strength=0.22,blur=18,dy=12):
    q=4; x0,y0,x1,y1=[v/q for v in box]
    m=Image.new('L',(CW//q,CH//q),0)
    ImageDraw.Draw(m).rounded_rectangle([x0,y0+dy*S/q,x1,y1+dy*S/q],radius=r/q,fill=int(255*strength))
    m=m.filter(ImageFilter.GaussianBlur(blur*S/q)).resize((CW,CH),Image.BICUBIC)
    sh=Image.new('RGBA',(CW,CH),(22,30,42,0)); sh.putalpha(m)
    frame.alpha_composite(sh)

def glass(frame,box,r,tint=0.62,blur=14,edge=True,shadow_s=0.22,shadow_blur=18,shadow_dy=12,backdrop=None):
    box=[int(round(v)) for v in box]
    if shadow_s>0: shadow(frame,box,r,shadow_s,shadow_blur,shadow_dy)
    src=backdrop if backdrop is not None else frame.convert('RGB')
    pad=blur*S*2
    cx0,cy0=max(0,box[0]-pad),max(0,box[1]-pad); cx1,cy1=min(CW,box[2]+pad),min(CH,box[3]+pad)
    if cx1<=cx0 or cy1<=cy0: return
    crop=src.crop((cx0,cy0,cx1,cy1)).filter(ImageFilter.GaussianBlur(blur*S))
    crop=Image.blend(crop,Image.new('RGB',crop.size,(250,251,252)),tint)
    m=rr_mask(crop.size,[box[0]-cx0,box[1]-cy0,box[2]-cx0,box[3]-cy0],r)
    layer=Image.new('RGBA',(CW,CH),(0,0,0,0)); c=crop.convert('RGBA'); c.putalpha(m); layer.paste(c,(cx0,cy0))
    frame.alpha_composite(layer)
    if edge:
        e=Image.new('RGBA',(CW,CH),(0,0,0,0)); d=ImageDraw.Draw(e)
        d.rounded_rectangle(box,radius=r,outline=(150,156,166,150),width=S)
        d.rounded_rectangle([box[0]+S,box[1]+S,box[2]-S,box[3]-S],radius=max(1,r-S),outline=(255,255,255,190),width=S)
        frame.alpha_composite(e)

# ---------- window ----------
def draw_arc(d,cx,cy,col,thick=6,r=17,a0=270,a1=360,alpha=255):
    t=thick*S; rr=r*S; n=40
    pts=[(cx+rr*math.cos(math.radians(a0+(a1-a0)*i/n)),cy+rr*math.sin(math.radians(a0+(a1-a0)*i/n))) for i in range(n+1)]
    d.line(pts,fill=col+(alpha,),width=int(round(t)),joint='curve')
    for px,py in (pts[0],pts[-1]):
        d.ellipse([px-t/2+0.5,py-t/2+0.5,px+t/2-0.5,py+t/2-0.5],fill=col+(alpha,))

def window_layer(frame,g,st):
    """g=(x,y,w,h) in 1x px. returns nothing; draws glass window + content onto frame (RGBA)."""
    x,y,w,h=g; X,Y,Wd,Ht=x*S,y*S,w*S,h*S; box=[X,Y,X+Wd,Y+Ht]
    lift=st.get('lift',0)
    R=st.get('r',24)*S
    glass(frame,box,R,tint=0.58,shadow_s=0.20+0.12*lift,shadow_blur=18+10*lift,shadow_dy=12+8*lift,backdrop=st.get('backdrop'))
    ca=st.get('content_alpha',1.0)
    lay=Image.new('RGBA',(CW,CH),(0,0,0,0)); d=ImageDraw.Draw(lay)
    if ca>0.01:
        A=lambda a: int(a*ca)
        # sidebar
        sbw=min(104,w*0.26)
        d.rounded_rectangle([X+12*S,Y+28*S,X+(12+sbw)*S,Y+Ht-12*S],radius=14*S,fill=(255,255,255,A(110)),outline=(255,255,255,A(170)),width=S)
        for i in range(5):
            yy=Y+(44+i*22)*S
            if yy>Y+Ht-26*S: break
            d.rounded_rectangle([X+24*S,yy,X+34*S,yy+10*S],radius=3*S,fill=SKEL+(A(255),))
            d.rounded_rectangle([X+40*S,yy+2*S,X+(40+sbw*0.5-(i%2)*10)*S,yy+8*S],radius=3*S,fill=SKEL+(A(200),))
        mx=X+(12+sbw+16)*S; mw=Wd-(12+sbw+16+16)*S
        d.text((mx,Y+34*S),st.get('app','Programming'),font=font(15,'SemiBold'),fill=TXT+(A(255),))
        d.text((mx,Y+54*S),'NCOM Arch window',font=font(9.5,'Medium'),fill=TXT2+(A(255),))
        for i,f in enumerate([.92,.84,.88,.6]):
            yy=Y+(76+i*13)*S
            if yy>Y+Ht-30*S: break
            d.rounded_rectangle([mx,yy,mx+mw*f,yy+6*S],radius=3*S,fill=SKEL+(A(170),))
        cy0=Y+136*S
        if cy0+40*S<Y+Ht-12*S:
            cwid=(mw-10*S)/2
            for k in range(2):
                cx0=mx+k*(cwid+10*S)
                d.rounded_rectangle([cx0,cy0,cx0+cwid,min(Y+Ht-14*S,cy0+(Ht/S-150)*S)],radius=14*S,fill=(255,255,255,A(120)),outline=(255,255,255,A(180)),width=S)
                d.rounded_rectangle([cx0+12*S,cy0+12*S,cx0+cwid*0.55,cy0+18*S],radius=3*S,fill=SKEL+(A(220),))
                d.rounded_rectangle([cx0+12*S,cy0+26*S,cx0+cwid*0.8,cy0+31*S],radius=3*S,fill=SKEL+(A(150),))
    # controls on the top line
    ctrl_a=st.get('ctrl_alpha',1.0)
    if ctrl_a>0.01:
        A=int(255*ctrl_a)
        cx=X+Wd-24*S; cy=Y+24*S
        ao=st.get('arc_off',(0,0)); ac=ACT if st.get('arc_on') else CTRL
        draw_arc(d,cx+ao[0]*S,cy+ao[1]*S,ac,alpha=A)
        po=st.get('pill_off',(0,0)); pw=st.get('pill_w',28); pc=ACT if st.get('pill_on') else CTRL
        pr=X+Wd-40*S+po[0]*S; pyc=Y+7*S+po[1]*S
        d.rounded_rectangle([pr-pw*S,pyc-3*S,pr,pyc+3*S],radius=3*S,fill=pc+(A,))
        da=st.get('dots_alpha',1.0)
        if da>0.01:
            dc=ACT if st.get('dots_on') else CTRL
            mcx=X+Wd/2; 
            if st.get('dots_held'):
                d.rounded_rectangle([mcx-20*S,Y+7*S-8*S,mcx+20*S,Y+7*S+8*S],radius=8*S,fill=(255,255,255,int(150*da)),outline=(150,156,166,int(120*da)),width=S)
            for k in (-1,0,1):
                px=mcx+k*9*S; d.ellipse([px-2.6*S,Y+7*S-2.6*S,px+2.6*S,Y+7*S+2.6*S],fill=dc+(int(A*da),))
        ha=st.get('handle_alpha',0)
        if ha>0.01:
            draw_arc(d,X+Wd-24*S,Y+Ht-24*S,ACT if st.get('handle_on') else CTRL,a0=0,a1=90,alpha=int(255*ha))
    frame.alpha_composite(lay)

def finger(frame,f):
    if not f or f.get('a',1)<=0.01: return
    x,y=f['x']*S,f['y']*S; a=f.get('a',1); p=f.get('p',0)
    lay=Image.new('RGBA',(CW,CH),(0,0,0,0)); d=ImageDraw.Draw(lay)
    r=(15-3*p)*S
    d.ellipse([x-r,y-r,x+r,y+r],fill=(30,34,42,int(a*(34+40*p))),outline=(255,255,255,int(a*210)),width=int(2*S))
    if f.get('ripple') is not None:
        q=f['ripple']; rr=(14+22*q)*S
        d.ellipse([x-rr,y-rr,x+rr,y+rr],outline=(30,34,42,int(a*160*(1-q))),width=int(2*S))
    frame.alpha_composite(lay)

def caption(frame,text,sub=None):
    f=font(12,'SemiBold'); tw=f.getlength(text)
    f2=font(10,'Medium'); sw=f2.getlength(sub) if sub else 0
    w=max(tw,sw)+28*S; h=(26 if not sub else 40)*S
    x0=(CW-w)/2; y0=12*S
    glass(frame,[x0,y0,x0+w,y0+h],h/2 if not sub else 14*S,tint=0.7,shadow_s=0.12,shadow_blur=10,shadow_dy=4)
    d=ImageDraw.Draw(frame)
    d.text(((CW-tw)/2,y0+6*S),text,font=f,fill=TXT)
    if sub: d.text(((CW-sw)/2,y0+22*S),sub,font=f2,fill=TXT2)

def dock(frame,hi=None,chip=None):
    w=150; x0=(W-w)/2; y0=H-42
    glass(frame,[x0*S,y0*S,(x0+w)*S,(y0+32)*S],16*S,tint=0.6,shadow_s=0.14,shadow_blur=10,shadow_dy=5)
    d=ImageDraw.Draw(frame)
    for i in range(4):
        ix=x0+12+i*34; d.rounded_rectangle([ix*S,(y0+6)*S,(ix+20)*S,(y0+26)*S],radius=6*S,fill=(160,166,175) if i!=1 else (120,126,136))
    if chip:  # minimized chip beside dock
        a=chip.get('a',1)
        cx0=x0+w+10
        sub=Image.new('RGBA',(CW,CH),(0,0,0,0))
        dd=ImageDraw.Draw(sub)
        dd.rounded_rectangle([cx0*S,y0*S,(cx0+96)*S,(y0+32)*S],radius=16*S,fill=(248,249,251,int(215*a)),outline=(150,156,166,int(150*a)),width=S)
        dd.rounded_rectangle([(cx0+8)*S,(y0+8)*S,(cx0+24)*S,(y0+24)*S],radius=5*S,fill=(120,126,136,int(255*a)))
        dd.text(((cx0+30)*S,(y0+9)*S),'Programming',font=font(10,'SemiBold'),fill=TXT+(int(255*a),))
        frame.alpha_composite(sub)

def scale_layer(layer,k,cx,cy,alpha=1.0):
    if abs(k-1)>1e-3:
        nw,nh=max(1,int(CW*k)),max(1,int(CH*k))
        sm=layer.resize((nw,nh),Image.BICUBIC)
        out=Image.new('RGBA',(CW,CH),(0,0,0,0))
        out.paste(sm,(int(cx*S-cx*S*k),int(cy*S-cy*S*k)))
        layer=out
    if alpha<0.999:
        a=layer.getchannel('A').point(lambda p:int(p*alpha)); layer.putalpha(a)
    return layer

def warp_layer(layer,cx,cy,dx,dy,sigma):
    """bubble: pull pixels near (cx,cy) by (dx,dy) with gaussian falloff (inverse map)."""
    arr=np.asarray(layer).astype(np.float32)
    yy,xx=np.mgrid[0:CH,0:CW].astype(np.float32)
    # iterate inverse: src = p - d(src) ~ p - d(p - d(p))
    sx,sy=xx.copy(),yy.copy()
    for _ in range(3):
        wgt=np.exp(-(((sx-cx*S)**2+(sy-cy*S)**2)/(2*(sigma*S)**2)))
        sx=xx-dx*S*wgt; sy=yy-dy*S*wgt
    x0=np.clip(np.floor(sx).astype(int),0,CW-2); y0=np.clip(np.floor(sy).astype(int),0,CH-2)
    fx=(sx-x0)[...,None]; fy=(sy-y0)[...,None]
    fx=np.clip(fx,0,1); fy=np.clip(fy,0,1)
    out=(arr[y0,x0]*(1-fx)*(1-fy)+arr[y0,x0+1]*fx*(1-fy)+arr[y0+1,x0]*(1-fx)*fy+arr[y0+1,x0+1]*fx*fy)
    return Image.fromarray(np.clip(out,0,255).astype(np.uint8),'RGBA')

SYMBOL=None
def symbol():
    global SYMBOL
    if SYMBOL is None:
        s=Image.open(os.environ.get('NCOM_SYMBOL',os.path.join(HERE,'..','..','assets','brand','NCOM-symbol.png'))).convert('RGBA')
        SYMBOL=s
    return SYMBOL

def popover(frame,anchor_r,anchor_y,p):
    """info popover under the window's top-right corner; p 0..1 grow"""
    if p<=0.01: return
    w,h=210,196; k=lerp(0.55,1,eout(p)); a=clamp(p*1.8)
    x1=anchor_r; x0=x1-w; y0=anchor_y
    lay=Image.new('RGBA',(CW,CH),(0,0,0,0))
    glass(lay,[x0*S,y0*S,x1*S,(y0+h)*S],20*S,tint=0.62,shadow_s=0.22,backdrop=frame.convert('RGB'))
    cl=Image.new('RGBA',(CW,CH),(0,0,0,0)); d=ImageDraw.Draw(cl)
    bx0,by0,bx1,by1=int((x0+8)*S),int((y0+8)*S),int((x1-8)*S),int((y0+78)*S)
    gw,gh=bx1-bx0,by1-by0
    gn=np.linspace(0,1,gw)[None,:,None]; gv=np.linspace(0,1,gh)[:,None,None]
    col=(np.array([92,98,108])*(1-gn)+np.array([170,176,185])*gn)*(1-0.22*gv)
    gl=Image.fromarray(np.ascontiguousarray(np.broadcast_to(col,(gh,gw,3))).astype(np.uint8)).convert('RGBA')
    sym=symbol().copy(); sym.thumbnail((int(70*S),int(44*S)),Image.LANCZOS)
    r_,g_,b_,a_=sym.split(); L=Image.merge('RGB',(r_,g_,b_)).convert('L').point(lambda v:int(205+v*0.19))
    gl.alpha_composite(Image.merge('RGBA',(L,L,L,a_)),(int(gw-sym.size[0]-12*S),int((gh-sym.size[1])/2)))
    ImageDraw.Draw(gl).text((10*S,gh-24*S),'Programming',font=font(13,'SemiBold'),fill=(250,251,252,255))
    gl.putalpha(ImageChops.multiply(gl.getchannel('A'),rr_mask(gl.size,[0,0,gw-1,gh-1],13*S)))
    lay.alpha_composite(gl,(bx0,by0))
    d.text(((x0+12)*S,(y0+86)*S),'About',font=font(10.5,'SemiBold'),fill=TXT)
    d.text(((x0+12)*S,(y0+101)*S),'Programming · v1.2 · NCOM Systems',font=font(8.5,'Medium'),fill=TXT2)
    d.rounded_rectangle([(x0+12)*S,(y0+116)*S,(x1-40)*S,(y0+120)*S],radius=2*S,fill=SKEL)
    for i,lbl in enumerate(['Option 1','Option 2']):
        oy=y0+130+i*30
        d.rounded_rectangle([(x0+8)*S,oy*S,(x1-8)*S,(oy+26)*S],radius=10*S,fill=(255,255,255,140),outline=(255,255,255,200),width=S)
        d.text(((x0+18)*S,(oy+7)*S),lbl,font=font(10,'Medium'),fill=TXT)
        d.text(((x1-22)*S,(oy+4)*S),'›',font=font(12,'Medium'),fill=TXT2)
    lay.alpha_composite(cl)
    frame.alpha_composite(scale_layer(lay,k,x1,y0,alpha=a))

def menubar(frame,cx,cy,p,sel=None,drop=0):
    if p<=0.01: return
    items=['File','Edit','View']; f=font(10.5,'SemiBold')
    full=sum(f.getlength(t) for t in items)/S+3*24+12
    w=lerp(40,full,eout(p)); h=22
    x0=cx-w/2; y0=cy-h/2
    glass(frame,[x0*S,y0*S,(x0+w)*S,(y0+h)*S],11*S,tint=0.62,shadow_s=0.16,shadow_blur=10,shadow_dy=4)
    ov=Image.new('RGBA',(CW,CH),(0,0,0,0)); d=ImageDraw.Draw(ov); ta=clamp((p-0.45)/0.55)
    xx=cx-full/2+6+12; pos={}
    for t in items:
        tw=f.getlength(t)/S
        if sel==t:
            d.rounded_rectangle([(xx-8)*S,(y0+3)*S,(xx+tw+8)*S,(y0+h-3)*S],radius=8*S,fill=(90,96,106,int(60*ta)))
        d.text((xx*S,(y0+5)*S),t,font=f,fill=TXT+(int(255*ta),)); pos[t]=(xx,tw); xx+=tw+24
    frame.alpha_composite(ov)
    if drop>0.01 and sel:
        sx,_=pos[sel]; dw,dh=128,4*24+10; dx0=sx-8; dy0=y0+h+6
        k=eout(drop)
        sub=Image.new('RGBA',(CW,CH),(0,0,0,0))
        glass(sub,[dx0*S,dy0*S,(dx0+dw)*S,(dy0+dh*k)*S],14*S,tint=0.62,shadow_s=0.2,backdrop=frame.convert('RGB'))
        ds=ImageDraw.Draw(sub)
        for i,t in enumerate(['New','Open…','Save','Export']):
            ty=dy0+7+i*24
            if ty+16>dy0+dh*k: break
            ds.text(((dx0+12)*S,(ty+3)*S),t,font=font(10,'Medium'),fill=TXT)
            ds.text(((dx0+dw-34)*S,(ty+4)*S),['⌘N','⌘O','⌘S','⌘E'][i],font=font(8.5,'Medium'),fill=TXT2)
        sub.putalpha(sub.getchannel('A').point(lambda v:int(v*clamp(drop*2))))
        frame.alpha_composite(sub)
    return pos

def save_gif(frames,out):
    tmp=out+'.d'; os.makedirs(tmp,exist_ok=True)
    for i,f in enumerate(frames): f.save(f'{tmp}/{i:03d}.png')
    cmd=['timeout','-k','5','80','ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',f'{tmp}/%03d.png',
         '-vf','split[a][b];[a]palettegen=max_colors='+os.environ.get('NCOM_COLORS','128')+':stats_mode=full[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle','-loop','0',out]
    subprocess.run(cmd,check=True)
    frames[0].save(out.replace('.gif','.first.png'))
    shutil.rmtree(tmp)
