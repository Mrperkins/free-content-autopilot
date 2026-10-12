"""Original typographic graphics and voice using FFmpeg + free local TTS."""
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

REGULAR=['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
BOLD=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
      '/usr/share/fonts/truetype/lato/Lato-Bold.ttf']

def font(size,bold=False):
    for path in (BOLD if bold else REGULAR):
        if Path(path).exists(): return ImageFont.truetype(path,size)
    return ImageFont.load_default()

def wrap_pixels(draw,text,face,width):
    lines=[];current=''
    for word in str(text).split():
        line=(current+' '+word).strip()
        if draw.textbbox((0,0),line,font=face)[2]>width and current:
            lines.append(current)
            current=word
        else: current=line
    if current: lines.append(current)
    return lines

def card(scene,idx,total,kind,path):
    W,H=(720,1280) if kind=='short' else (1280,720)
    seed=int(hashlib.sha256(scene['headline'].encode()).hexdigest()[:8],16)
    base=(17+seed%14,24+seed//19%16,38+seed//223%18)
    accent=(70+seed%60,153+seed%65,197+seed%50)
    canvas=Image.new('RGB',(W,H))
    d=ImageDraw.Draw(canvas)
    for y in range(H):
        factor=y/H
        d.line((0,y,W,y),fill=tuple(min(255,int(channel+(i+1)*24*factor))
                                   for i,channel in enumerate(base)))
    center=(int(W*.88),int(H*.25))
    for n in range(9):
        r=int(W*(.1+n*.06))
        d.ellipse((center[0]-r,center[1]-r,center[0]+r,center[1]+r),
                  outline=accent,width=2 if n%2==0 else 1)
    top=int(H*.18);left=int(W*.09);limit=int(W*.82)
    d.rounded_rectangle((left,top-42,left+min(W*.35,300),top-7),
                        10,fill=accent)
    d.text((left+10,top-40),'ORIGINAL EXPLAINER',
           font=font(17,True),fill=(5,15,25))
    title_font=font(55 if kind=='short' else 65,True)
    lines=wrap_pixels(d,scene['headline'],title_font,limit)
    if len(lines)>5: raise RuntimeError('Headline too long for rendering')
    for n,line in enumerate(lines):
        d.text((left,top+20+n*(title_font.size+17)),line,
               font=title_font,fill='white')
    note_font=font(22 if kind=='short' else 19)
    for n,line in enumerate(wrap_pixels(d,scene.get('visual_note','')[:90],
                                       note_font,limit)[:2]):
        d.text((left,int(H*.79)+n*34),line,font=note_font,fill=(184,199,214))
    d.rectangle((left,H-91,W-left,H-89),fill=(80,91,106))
    d.rectangle((left,H-91,left+int((W-2*left)*(idx+1)/total),H-89),fill=accent)
    d.text((left,H-65),f'{idx+1:02d} / {total:02d}',
           font=font(19),fill=(195,208,221))
    canvas.save(path)

def run(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)

def render(draft_path,output_dir):
    voice=shutil.which('espeak-ng') or shutil.which('espeak')
    if not shutil.which('ffmpeg') or not voice:
        raise RuntimeError('Install free ffmpeg and espeak-ng to render')
    item=json.loads(Path(draft_path).read_text())
    kind=item['format']
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td);parts=[]
        for index,scene in enumerate(item['scenes']):
            png=temp/f'{index}.png'
            wav=temp/f'{index}.wav'
            mp4=temp/f'{index}.mp4'
            card(scene,index,len(item['scenes']),kind,png)
            run([voice,'-s','155','-p','49','-v','en-us','-w',str(wav),scene['narration']])
            run(['ffmpeg','-y','-loop','1','-framerate','25','-i',str(png),'-i',str(wav),
                 '-c:v','libx264','-preset','veryfast','-crf','28','-pix_fmt','yuv420p',
                 '-c:a','aac','-b:a','96k','-shortest','-movflags','+faststart',str(mp4)])
            parts.append(mp4)
        playlist=temp/'segments.txt'
        playlist.write_text(''.join("file '"+str(p)+"'\n" for p in parts))
        target=output/'video.mp4'
        run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(playlist),
             '-c','copy','-movflags','+faststart',str(target)])
    (output/'draft.json').write_text(json.dumps(item,indent=2,ensure_ascii=False))
    return target
