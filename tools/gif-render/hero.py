# NCOM Arch README hero banner (1200x500): what it is, why it's better (bold, in the banner), and the gestures live on the right.
# Usage: python3 hero.py <out.gif> [out.png]
import sys, os, shutil, subprocess
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import scenes as SC
from ncom_core import np, FONT, CW, CH
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
HW,HH=1200,500
def fnt(sz,wt='Medium'):
    f=ImageFont.truetype(FONT,int(sz))
    try: f.set_variation_by_name(wt)
    except Exception: pass
    return f
def find_logo():
    for p in [os.path.join(HERE,'..','..','assets','brand','NCOM-Arch-logo.png'),'/home/user/tab/files/ncom-arch/repo/assets/brand/NCOM-Arch-logo.png']:
        if os.path.exists(p): return p
# right-hand live demo: the real gesture scenes, shown in dark mode
SCENE_LIST=[('arc_close',2.45),('pill_minimize',2.45),('pill_info',4.9),('dots_menu',3.5),('dots_snap',2.95),('resize',3.0)]
PX0,PY0,PW=612,78,540; PH=int(PW*CH/CW)
FPSH=float(os.environ.get('HERO_FPS','6'))
def background():
    y=np.linspace(0,1,HH)[:,None,None]; x=np.linspace(0,1,HW)[None,:,None]
    g=np.array([24,27,33])*(1-y)+np.array([10,12,15])*y+0*x
    im=Image.fromarray(g.astype(np.uint8),'RGB').convert('RGBA')
    glow=Image.new('L',(HW//4,HH//4),0); d=ImageDraw.Draw(glow)
    d.ellipse([HW/4*0.52,HH/4*0.05,HW/4*1.02,HH/4*1.0],fill=70); d.ellipse([-HW/4*0.1,HH/4*0.45,HW/4*0.35,HH/4*1.3],fill=40)
    glow=glow.filter(ImageFilter.GaussianBlur(30)).resize((HW,HH),Image.BICUBIC)
    im.alpha_composite(Image.merge('RGBA',[Image.new('L',(HW,HH),v) for v in (120,130,150)]+[glow]))
    return im
def left_column(im):
    d=ImageDraw.Draw(im)
    lg=Image.open(find_logo()).convert('RGBA').resize((64,64),Image.LANCZOS); im.alpha_composite(lg,(52,44))
    d.text((128,52),'NCOM Arch',font=fnt(32,'Bold'),fill=(246,248,251))
    tw=fnt(32,'Bold').getlength('NCOM Arch')
    tag='Window system for N•OS'; ft=fnt(14,'SemiBold'); w=ft.getlength(tag)+22
    tg=Image.new('RGBA',(HW,HH),(0,0,0,0)); ImageDraw.Draw(tg).rounded_rectangle([128+tw+14,58,128+tw+14+w,84],radius=13,fill=(255,255,255,26),outline=(255,255,255,70))
    im.alpha_composite(tg); d=ImageDraw.Draw(im)
    d.text((128+tw+25,62),tag,font=ft,fill=(214,220,228))
    d.text((56,134),'Glass windows you drive with gestures, not buttons.',font=fnt(19,'Medium'),fill=(176,184,196))
    # the WHY, big and bold
    fh=fnt(56,'ExtraBold')
    d.text((54,166),'No title bars.',font=fh,fill=(255,255,255))
    d.text((54,230),'No tiny buttons.',font=fh,fill=(255,255,255))
    # callout: where the controls went
    box=[56,314,566,404]
    cl=Image.new('RGBA',(HW,HH),(0,0,0,0)); dc=ImageDraw.Draw(cl)
    dc.rounded_rectangle(box,radius=18,fill=(255,255,255,22),outline=(255,255,255,60),width=1)
    gl=Image.new('RGBA',(HW,HH),(0,0,0,0)); dg=ImageDraw.Draw(gl)
    dg.rounded_rectangle([box[0]+12,box[1]+16,box[0]+18,box[3]-16],radius=3,fill=(250,252,255,255))
    cl.alpha_composite(gl.filter(ImageFilter.GaussianBlur(6))); cl.alpha_composite(gl)
    im.alpha_composite(cl); d=ImageDraw.Draw(im)
    fb=fnt(29,'Bold')
    d.text((box[0]+34,box[1]+10),'Every control lives in',font=fb,fill=(255,255,255))
    d.text((box[0]+34,box[1]+46),"the window's corners.",font=fb,fill=(255,255,255))
    d.text((56,424),'Flick the arc to close  ·  swipe the pill to min/max  ·  hold ••• to snap',font=fnt(15,'Medium'),fill=(150,158,170))
def panel_mask():
    m=Image.new('L',(PW*2,PH*2),0); ImageDraw.Draw(m).rounded_rectangle([0,0,PW*2-1,PH*2-1],radius=44,fill=255)
    return m.resize((PW,PH),Image.LANCZOS)
def static_base():
    im=background(); left_column(im)
    sh=Image.new('RGBA',(HW,HH),(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle([PX0-2,PY0+10,PX0+PW+2,PY0+PH+18],radius=26,fill=(0,0,0,150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    ring=Image.new('RGBA',(HW,HH),(0,0,0,0)); ImageDraw.Draw(ring).rounded_rectangle([PX0-1,PY0-1,PX0+PW,PY0+PH],radius=23,outline=(255,255,255,90),width=2)
    im.alpha_composite(ring)
    return im
def compose(base,mask,scene_rgb,idx):
    im=base.copy()
    sc=ImageOps.invert(scene_rgb.convert('RGB')).resize((PW,PH),Image.LANCZOS)
    a=np.asarray(sc).astype(np.float32); g=a.mean(axis=2,keepdims=True)
    a=(0.25*a+0.75*g)*np.array([0.93,0.97,1.06]); sc=Image.fromarray(np.clip(a,0,255).astype(np.uint8))   # neutral cool dark mode
    im.paste(sc,(PX0,PY0),mask)
    d=ImageDraw.Draw(im); n=len(SCENE_LIST); cx=PX0+PW/2; y=PY0+PH+30
    for i in range(n):
        x=cx+(i-(n-1)/2)*20
        if i==idx: d.rounded_rectangle([x-9,y-4,x+9,y+4],radius=4,fill=(250,252,255))
        else: d.ellipse([x-4,y-4,x+4,y+4],fill=(110,116,126))
    return im.convert('RGB')
def frames():
    base=static_base(); mask=panel_mask()
    for idx,(name,T) in enumerate(SCENE_LIST):
        fn=SC.SCENES[name]; n=int(round(T*FPSH))
        for i in range(n):
            yield compose(base,mask,fn(min(T-1e-3,i/FPSH))[0],idx), (i==n-1)
def still(t_scene=('dots_menu',2.4)):
    base=static_base(); mask=panel_mask(); name,t=t_scene
    idx=[s[0] for s in SCENE_LIST].index(name)
    return compose(base,mask,SC.SCENES[name](t)[0],idx)
if __name__=='__main__':
    out=sys.argv[1]; tmp=out+'.d'; os.makedirs(tmp,exist_ok=True); k=0
    for im,last in frames():
        for _ in range(4 if last else 1):   # hold each gesture's result
            im.save(f'{tmp}/{k:04d}.png'); k+=1
    subprocess.run(['timeout','-k','5','170','ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-framerate',str(FPSH),'-i',f'{tmp}/%04d.png',
        '-vf','split[a][b];[a]palettegen=max_colors='+os.environ.get('HERO_COLORS','72')+':stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle','-loop','0',out],check=True)
    shutil.rmtree(tmp)
    if len(sys.argv)>2: still().save(sys.argv[2],optimize=True)
    print('frames',k,'bytes',os.path.getsize(out))
