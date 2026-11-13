from flask import Flask, render_template, request, jsonify, send_from_directory
import os, json, re, uuid, asyncio, requests
from datetime import datetime
from renderer import render_video, get_all_voices

APP_DIR=os.path.dirname(os.path.abspath(__file__))
PROJECTS=os.path.join(APP_DIR,"projects")
os.makedirs(PROJECTS,exist_ok=True)
app=Flask(__name__)
app.secret_key="oscar-ai-studio-local"
_voices=None
OLLAMA_URL="http://127.0.0.1:11434"

def split_scenes(story, limit=420):
    parts=[p.strip() for p in re.split(r'\n+|(?<=[।.!?])\s+',story) if p.strip()]
    scenes=[]; cur=""
    for p in parts:
        if cur and len(cur)+len(p)>limit:
            scenes.append(cur); cur=p
        else: cur=(cur+" "+p).strip()
    if cur: scenes.append(cur)
    return scenes or [story]

def save(d):
    pid=datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+uuid.uuid4().hex[:5]
    d["id"]=pid; d["created"]=datetime.now().isoformat(timespec="seconds")
    with open(os.path.join(PROJECTS,pid+".json"),"w",encoding="utf-8") as f:
        json.dump(d,f,ensure_ascii=False,indent=2)
    return pid

@app.get("/")
def home():
    projects=[]
    for fn in sorted(os.listdir(PROJECTS),reverse=True):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(PROJECTS,fn),encoding="utf-8") as f: d=json.load(f)
                projects.append({"title":d.get("title","Untitled"),"created":d.get("created","")})
            except Exception: pass
    return render_template("index.html",projects=projects[:15])

@app.get("/api/ollama")
def ollama_status():
    try:
        r=requests.get(OLLAMA_URL+"/api/tags",timeout=3); r.raise_for_status()
        models=[m.get("name","") for m in r.json().get("models",[])]
        return jsonify(available=True,models=models)
    except Exception:
        return jsonify(available=False,models=[],help="Install and start Ollama, then download a model such as llama3.2:3b.")

@app.post("/api/write-story")
def write_story():
    data=request.get_json(force=True)
    prompt=(data.get("prompt") or "").strip()
    language=(data.get("language") or "Bengali").strip()
    genre=(data.get("genre") or "Adventure").strip()
    minutes=max(1,min(30,int(data.get("minutes") or 5)))
    if not prompt: return jsonify(error="গল্পের বিষয় বা Prompt লিখুন।"),400
    model=(data.get("model") or "llama3.2:3b").strip()
    system=("You are a creative story writer. Write an original, engaging story. "
            "Return only the story, without analysis, headings about your process, or markdown. "
            "Use clear paragraphs and natural dialogue. Do not add scene labels.")
    user=(f"Write a {genre} story in {language}. Target narration duration: about {minutes} minutes. "
          f"Approximate 120-140 spoken words per minute where appropriate. Story idea: {prompt}")
    try:
        r=requests.post(OLLAMA_URL+"/api/chat",json={
            "model":model,"stream":False,
            "messages":[{"role":"system","content":system},{"role":"user","content":user}],
            "options":{"temperature":0.8}
        },timeout=900)
        r.raise_for_status()
        story=r.json().get("message",{}).get("content","").strip()
        if not story: raise RuntimeError("AI returned an empty story.")
        return jsonify(story=story,model=model)
    except requests.exceptions.ConnectionError:
        return jsonify(error="Ollama চালু নেই। Ollama ইনস্টল করে চালু করুন, তারপর llama3.2:3b model ডাউনলোড করুন।"),503
    except requests.exceptions.Timeout:
        return jsonify(error="AI model-এর উত্তর পেতে বেশি সময় লাগছে। ছোট গল্প বা হালকা model দিয়ে চেষ্টা করুন।"),504
    except Exception as e:
        return jsonify(error="AI story তৈরি হয়নি: "+str(e)),500

@app.get("/api/voices")
def voices():
    global _voices
    try:
        if _voices is None: _voices=asyncio.run(get_all_voices())
        return jsonify(voices=_voices)
    except Exception as e: return jsonify(voices=[],error=str(e)),502

@app.post("/api/project")
def create():
    d=request.get_json(force=True)
    story=(d.get("story") or "").strip()
    if not story: return jsonify(error="গল্প লিখুন।"),400
    d["title"]=(d.get("title") or "আমার গল্প").strip()
    d["scenes"]=[{"number":i+1,"text":s} for i,s in enumerate(split_scenes(story))]
    d["status"]="Storyboard ready"
    # Exportable image-generation prompts, one per scene; no image generation is claimed.
    style=d.get("visual_style","cinematic story illustration")
    d["image_prompts"]=[f"{style}, scene {i+1}: {s[:500]}, consistent characters, no text, no watermark"
                        for i,s in enumerate([x["text"] for x in d["scenes"]])]
    pid=save(d)
    promptfile=os.path.join(PROJECTS,pid+"_image_prompts.txt")
    with open(promptfile,"w",encoding="utf-8-sig") as f:
        for i,p in enumerate(d["image_prompts"],1): f.write(f"SCENE {i}\n{p}\n\n")
    return jsonify(id=pid,scenes=d["scenes"],image_prompt_url="/file/projects/"+pid+"_image_prompts.txt",
                   message="Storyboard ও Scene Image Prompts তৈরি হয়েছে।")


@app.post("/api/project/<pid>/scene/<int:scene_no>/image")
def upload_scene_image(pid, scene_no):
    project_path=os.path.join(PROJECTS,pid+".json")
    if not os.path.isfile(project_path): return jsonify(error="Project পাওয়া যায়নি।"),404
    if "image" not in request.files: return jsonify(error="ছবি নির্বাচন করুন।"),400
    f=request.files["image"]
    ext=os.path.splitext(f.filename or "")[1].lower()
    if ext not in (".png",".jpg",".jpeg",".webp"):
        return jsonify(error="শুধু PNG, JPG, JPEG বা WEBP ছবি দিন।"),400
    with open(project_path,encoding="utf-8") as fp: d=json.load(fp)
    if scene_no<1 or scene_no>len(d.get("scenes",[])): return jsonify(error="Scene number ভুল।"),400
    folder=os.path.join(PROJECTS,pid,"scene_images"); os.makedirs(folder,exist_ok=True)
    target=os.path.join(folder,f"scene_{scene_no:03d}{ext}")
    f.save(target)
    d["scenes"][scene_no-1]["image"]=os.path.relpath(target,APP_DIR).replace("\\","/")
    with open(project_path,"w",encoding="utf-8") as fp: json.dump(d,fp,ensure_ascii=False,indent=2)
    return jsonify(message="Scene image যোগ হয়েছে।",url="/file/"+d["scenes"][scene_no-1]["image"])


@app.post("/api/project/<pid>/scene/<int:scene_no>/generate-image")
def generate_scene_image(pid, scene_no):
    project_path=os.path.join(PROJECTS,pid+".json")
    if not os.path.isfile(project_path): return jsonify(error="Project পাওয়া যায়নি।"),404
    data=request.get_json(force=True)
    api_key=(data.get("api_key") or "").strip()
    if not api_key: return jsonify(error="Pollinations API key দিন।"),400
    with open(project_path,encoding="utf-8") as fp: d=json.load(fp)
    scenes=d.get("scenes",[])
    if scene_no<1 or scene_no>len(scenes): return jsonify(error="Scene number ভুল।"),400
    ratio=d.get("ratio","16:9")
    dims={"16:9":(1280,720),"9:16":(720,1280),"1:1":(1024,1024),"4:5":(832,1040),"4:3":(1024,768)}
    width,height=dims.get(ratio,(1024,1024))
    model=(data.get("model") or "black-forest-labs/flux.1-schnell").strip()
    allowed={"black-forest-labs/flux.1-schnell","tongyi-mai/z-image-turbo","black-forest-labs/flux.2-klein-4b"}
    if model not in allowed: return jsonify(error="এই build-এ অনুমোদিত image model নির্বাচন করুন।"),400
    scene=scenes[scene_no-1]
    prompts=d.get("image_prompts",[])
    prompt=(prompts[scene_no-1] if len(prompts)>=scene_no else scene.get("text",""))
    prompt=(prompt+"; high quality story illustration, cinematic composition, consistent recurring character design, no text, no logo, no watermark")[:1800]
    import urllib.parse
    url="https://gen.pollinations.ai/image/"+urllib.parse.quote(prompt,safe="")
    try:
        resp=requests.get(url,params={"model":model,"width":width,"height":height,"nologo":"true","private":"true"},headers={"Authorization":"Bearer "+api_key},timeout=(20,240))
        if resp.status_code in (401,403): return jsonify(error="API key গ্রহণ করা হয়নি। Pollinations account থেকে সঠিক key দিন।"),401
        if resp.status_code==402: return jsonify(error="এই API key-এর balance/budget যথেষ্ট নয়। Generation বিনামূল্যে বা unlimited নয়।"),402
        resp.raise_for_status()
        if not resp.headers.get("Content-Type","").lower().startswith("image/"): return jsonify(error="Provider থেকে image file আসেনি। অন্য model দিয়ে চেষ্টা করুন।"),502
        folder=os.path.join(PROJECTS,pid,"scene_images"); os.makedirs(folder,exist_ok=True)
        target=os.path.join(folder,f"scene_{scene_no:03d}_ai.jpg")
        with open(target,"wb") as out: out.write(resp.content)
        scene["image"]=os.path.relpath(target,APP_DIR).replace("\\","/")
        scene["image_source"]="Pollinations AI"
        with open(project_path,"w",encoding="utf-8") as fp: json.dump(d,fp,ensure_ascii=False,indent=2)
        return jsonify(message="AI image তৈরি হয়েছে।",url="/file/"+scene["image"],model=model)
    except requests.exceptions.Timeout: return jsonify(error="Image generation timeout হয়েছে। আবার চেষ্টা করুন।"),504
    except requests.exceptions.RequestException as e: return jsonify(error="Image generation ব্যর্থ: "+str(e)),502

@app.post("/api/project/<pid>/render")
def render(pid):
    path=os.path.join(PROJECTS,pid+".json")
    if not os.path.isfile(path): return jsonify(error="Project পাওয়া যায়নি।"),404
    with open(path,encoding="utf-8") as f: d=json.load(f)
    try:
        result=render_video(d,APP_DIR)
        d["status"]="Video and audio ready"
        for key in ("video","audio","subtitle"):
            d[key]=os.path.relpath(result[key],APP_DIR).replace("\\","/")
        with open(path,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
        return jsonify(message="ভিডিও, অডিও ও সাবটাইটেল তৈরি হয়েছে!",
            video_url="/file/"+d["video"],audio_url="/file/"+d["audio"],subtitle_url="/file/"+d["subtitle"])
    except Exception as e: return jsonify(error=str(e)),500

@app.get("/file/<path:name>")
def file(name): return send_from_directory(APP_DIR,name,as_attachment=True)

if __name__=="__main__":
    print("\\nOSCAR AI STUDIO v0.7 — http://127.0.0.1:5000")
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
