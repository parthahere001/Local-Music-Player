from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC
import os, json

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Paths
MUSIC_DIR = "static/music"
PLAYLIST_DIR = "static/playlists"
os.makedirs(PLAYLIST_DIR, exist_ok=True)

# Homepage
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Stream music file
@app.get("/music/{filename}")
def stream_music(filename: str):
    path = os.path.join(MUSIC_DIR, filename)
    return FileResponse(path)

# Song metadata
def get_metadata(file_name):
    path = os.path.join(MUSIC_DIR, file_name)
    try:
        audio = MutagenFile(path, easy=True)
        return {
            "name": file_name,
            "title": audio.get("title", [file_name])[0],
            "artist": audio.get("artist", ["Unknown Artist"])[0],
            "album": audio.get("album", ["Unknown Album"])[0],
            "duration": int(audio.info.length) if audio and audio.info else 0
        }
    except:
        return {
            "name": file_name,
            "title": file_name,
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "duration": 0
        }

@app.get("/api/songs")
def list_songs():
    files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(('.mp3', '.wav', '.flac'))]
    return JSONResponse([get_metadata(f) for f in files])

# Search endpoint
@app.get("/api/search")
def search(q: str):
    files = [f for f in os.listdir(MUSIC_DIR) if q.lower() in f.lower()]
    return JSONResponse([get_metadata(f) for f in files])

# Cover image API
@app.get("/api/cover/{filename}")
def get_cover(filename: str):
    path = os.path.join(MUSIC_DIR, filename)
    try:
        ext = filename.lower().split('.')[-1]
        if ext == "mp3":
            audio = MP3(path, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    return Response(content=tag.data, media_type=tag.mime)
        elif ext == "flac":
            audio = FLAC(path)
            if audio.pictures:
                return Response(content=audio.pictures[0].data, media_type=audio.pictures[0].mime)
    except:
        pass
    return Response(status_code=404)

# Save playlist
@app.post("/api/save_playlist")
def save_playlist(name: str = Form(...), songs: str = Form(...)):
    path = os.path.join(PLAYLIST_DIR, f"{name}.json")
    with open(path, 'w') as f:
        json.dump(json.loads(songs), f)
    return {"status": "saved"}

# Load playlist
@app.get("/api/load_playlist/{name}")
def load_playlist(name: str):
    path = os.path.join(PLAYLIST_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return JSONResponse(json.load(f))
    return JSONResponse([], status_code=404)
