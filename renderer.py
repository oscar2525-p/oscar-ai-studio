import os, asyncio, subprocess, textwrap
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import edge_tts
from mutagen.mp3 import MP3

async def get_all_voices():
    voices=await edge_tts.list_voices()
    return [{"id":v.get("ShortName",""),"name":v.get("FriendlyName",v.get("ShortName","")),
             "locale":v.get("Locale",""),"gender":v.get("Gender",""),
             "label":f'{v.get("Locale","")} • {v.get("Gender","")} • {v.get("FriendlyName",v.get("ShortName",""))}'}
            for v in voices]

def get_font(size):
    for p in [r"C:\Windows\Fonts\Nirmala.ttf",r"C:\Windows\Fonts\NirmalaB.ttf",r"C:\Windows\Fonts\arial.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p,size)
            except Exception: pass
    return ImageFont.load_default()

async def make_audio(text,voice,path,rate):
    await edge_tts.Communicate(text,voice,rate=rate).save(path)

def srt_time(seconds):
    ms=int(seconds*1000); h=ms//3600000; ms%=3600000
    m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def render_video(project,app_dir):
    scenes=project.get("scenes") or []
    if not scenes: raise RuntimeError("কোনো Scene নেই।")
    dims={"16:9":(1280,720),"9:16":(720,1280),"1:1":(900,900),"4:5":(864,1080),"4:3":(960,720)}
    w,h=dims.get(project.get("ratio","16:9"),(1280,720))
    root=os.path.join(app_dir,"projects",project["id"]); os.makedirs(root,exist_ok=True)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    voice=project.get("voice","bn-IN-BashkarNeural"); female=project.get("female_voice",voice)
    dual=project.get("voice_mode")=="dual"; rate=project.get("rate","+0%")
    audio_parts=[]
    for idx,scene in enumerate(scenes):
        txt=scene.get("text","").strip()
        if not txt: continue
        aud=os.path.join(root,f"audio_{idx:03d}.mp3")
        chosen=(female if idx%2 else voice) if dual else voice
        asyncio.run(make_audio(txt,chosen,aud,rate))
        audio_parts.append((aud,max(1.0,float(MP3(aud).info.length)),txt))
    if not audio_parts: raise RuntimeError("গল্পে ব্যবহারযোগ্য লেখা পাওয়া যায়নি।")
    concat_a=os.path.join(root,"audio_concat.txt")
    with open(concat_a,"w",encoding="utf-8") as f:
        for aud,_,_ in audio_parts: f.write("file '"+aud.replace("\\","/")+"'\n")
    audio_out=os.path.join(root,"OSCAR_Narration.mp3")
    p=subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",concat_a,"-c","copy",audio_out],capture_output=True,text=True)
    if p.returncode: raise RuntimeError("Audio join failed: "+p.stderr[-800:])
    elapsed=0.0; srt=os.path.join(root,"OSCAR_Subtitles.srt")
    with open(srt,"w",encoding="utf-8-sig") as f:
        for n,(_,dur,txt) in enumerate(audio_parts,1):
            f.write(f"{n}\n{srt_time(elapsed)} --> {srt_time(elapsed+dur)}\n{txt}\n\n"); elapsed+=dur
    segments=[]
    for idx,(aud,dur,txt) in enumerate(audio_parts):
        scene_image=scene.get("image")
        if scene_image and os.path.isfile(os.path.join(app_dir,scene_image)):
            from PIL import ImageEnhance
            img=Image.open(os.path.join(app_dir,scene_image)).convert("RGB").resize((w,h),Image.Resampling.LANCZOS)
            img=ImageEnhance.Brightness(img).enhance(0.68)
        else:
            img=Image.new("RGB",(w,h),(12,28,52)); bg=ImageDraw.Draw(img)
            for yy in range(h):
                shade=int(17+25*yy/h); bg.line((0,yy,w,yy),fill=(8,shade,min(100,shade+40)))
        draw=ImageDraw.Draw(img)
        draw.rounded_rectangle((24,20,w-24,h-20),radius=22,outline=(255,210,130),width=2)
        draw.text((42,35),project.get("title","OSCAR AI STORY"),font=get_font(28),fill=(255,220,160),stroke_width=2,stroke_fill="#000000")
        lines=[]
        for para in txt.splitlines() or [txt]: lines += textwrap.wrap(para,max(20,int(w/29))) or [""]
        font=get_font(32 if project.get("ratio")!="9:16" else 29); line_h=50 if project.get("ratio")!="9:16" else 44
        y=max(100,(h-len(lines)*line_h)//2)
        for line in lines:
            draw.text((42,y),line,font=font,fill="white",stroke_width=1,stroke_fill="#000000"); y+=line_h
        draw.text((42,h-55),f"OSCAR AI STUDIO  |  Scene {idx+1}/{len(audio_parts)}",font=get_font(18),fill=(180,200,225))
        image=os.path.join(root,f"scene_{idx:03d}.png"); img.save(image)
        seg=os.path.join(root,f"segment_{idx:03d}.mp4")
        vf=f"scale={w}:{h},zoompan=z='min(zoom+0.0005,1.03)':d=1:s={w}x{h}:fps=20,format=yuv420p"
        cmd=[ffmpeg,"-y","-loop","1","-i",image,"-i",aud,"-t",str(dur),"-vf",vf,"-r","20","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-b:a","96k","-shortest",seg]
        p=subprocess.run(cmd,capture_output=True,text=True)
        if p.returncode: raise RuntimeError("Scene render failed: "+p.stderr[-900:])
        segments.append(seg)
    concat_v=os.path.join(root,"video_concat.txt")
    with open(concat_v,"w",encoding="utf-8") as f:
        for seg in segments: f.write("file '"+seg.replace("\\","/")+"'\n")
    video_out=os.path.join(root,"OSCAR_AI_STORY.mp4")
    p=subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",concat_v,"-c","copy",video_out],capture_output=True,text=True)
    if p.returncode: raise RuntimeError("Final video failed: "+p.stderr[-900:])
    return {"video":video_out,"audio":audio_out,"subtitle":srt}
