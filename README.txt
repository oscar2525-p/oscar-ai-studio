OSCAR AI STUDIO v0.8 — Windows 10
===================================
INSTALL
1. Extract this ZIP to a NEW folder.
2. Install Python 3.10+ and tick "Add Python to PATH".
3. Double-click RUN_OSCAR.bat; wait for package installation.
4. Browser opens at http://127.0.0.1:5000. Keep terminal open.

OPTIONAL LOCAL AI STORY WRITER (FREE LOCAL INFERENCE)
1. Install Ollama for Windows from https://ollama.com/download
2. Open Command Prompt and run: ollama pull llama3.2:3b
3. Wait for the model download to finish.
4. Keep Ollama running; restart OSCAR AI STUDIO.
5. Enter a prompt, choose language/genre/duration and click Generate Story with Local AI.
If 3B is too slow or runs out of memory on an 8 GB PC, try a smaller available model such as qwen2.5:1.5b (if supported by your Ollama installation).

FEATURES
- Optional local story generation via Ollama API.
- Genre/language/duration-guided story prompt.
- Scene-by-scene image prompt TXT export.
- Edge TTS online voice generation.
- MP4, MP3 and SRT output; five aspect ratios.

LIMITATIONS
- Ollama model downloads require internet and disk space; generation runs locally afterward.
- Edge TTS narration still requires internet and provider availability.
- Image prompts are text only. This build does not generate actual AI images or character animation.
- Video scenes are text cards with subtle zoom.
- Try a short story first on 8 GB RAM.
- Project data is saved under projects.


NEW IN v0.7 — SCENE IMAGE IMPORT
After creating a storyboard, upload a PNG/JPG/JPEG/WEBP image for each scene. The video renderer uses it as the background with subtle zoom. Without an image, text-card visuals remain. This is image-assisted video rendering, not automatic AI image generation or character animation.


NEW IN v0.8 — AI SCENE IMAGE GENERATION
- Generate an image for one scene or attempt all scenes sequentially.
- Uses Pollinations API. Create a key at https://enter.pollinations.ai/
- Paste the key into the local app. It is sent to the local backend per request and is not saved in project JSON.
- Generation is not guaranteed free or unlimited; account credits, budgets, model access and terms apply. Never share your secret key.
- Generated image dimensions follow the selected video aspect ratio.
- Manual image upload remains available as fallback.
- Character consistency is prompted but not guaranteed.


RENDER FREE HOSTING NOTES
- This ZIP includes Gunicorn and Render deployment configuration.
- Upload the extracted files (not the ZIP itself) to a GitHub repository, then connect that repo to Render as a Python Web Service.
- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app --workers 1 --threads 4 --timeout 300
- Cloud hosting does NOT provide access to Ollama running on your Windows PC at 127.0.0.1:11434. Local Ollama story generation therefore works only when running on your PC, unless you separately configure a secure remote model endpoint.
- Render Free has an ephemeral filesystem. Uploaded scene images, project JSON, and generated media may be lost on restart, redeploy, or spin-down. Do not use it as permanent storage.
- Free services spin down after inactivity and can take about a minute to wake.
