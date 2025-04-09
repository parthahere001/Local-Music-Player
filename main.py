from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import os, json, uuid

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Folders to scan for .mp3 files
SEARCH_DIRS = [
    os.path.expanduser("~/Music"),
    os.path.expanduser("~/Downloads"),
]

PLAYLIST_DIR = "static/playlists"
os.makedirs(PLAYLIST_DIR, exist_ok=True)

# Store scanned song info
SONG_INDEX = {}

def scan_mp3_files():
    SONG_INDEX.clear()
    for root in SEARCH_DIRS:
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if fname.lower().endswith(".mp3"):
                    full_path = os.path.join(dirpath, fname)
                    try:
                        audio = MutagenFile(full_path, easy=True)
                        id = str(uuid.uuid4())
                        SONG_INDEX[id] = {
                            "id": id,
                            "path": full_path,
                            "title": audio.get("title", [fname])[0],
                            "artist": audio.get("artist", ["Unknown Artist"])[0],
                            "album": audio.get("album", ["Unknown Album"])[0],
                            "duration": int(audio.info.length) if audio and audio.info else 0,
                            "name": fname
                        }
                    except:
                        continue

scan_mp3_files()

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/songs")
def list_songs():
    return list(SONG_INDEX.values())

@app.get("/music/{song_id}")
def stream_by_id(song_id: str):
    song = SONG_INDEX.get(song_id)
    if not song:
        return Response(status_code=404)
    return FileResponse(song["path"])

@app.get("/api/cover/{song_id}")
def get_cover(song_id: str):
    song = SONG_INDEX.get(song_id)
    if not song:
        return Response(status_code=404)
    path = song["path"]
    try:
        audio = MP3(path, ID3=ID3)
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                return Response(content=tag.data, media_type=tag.mime)
    except:
        pass
    return Response(status_code=404)

@app.post("/api/save_playlist")
def save_playlist(name: str = Form(...), songs: str = Form(...)):
    path = os.path.join(PLAYLIST_DIR, f"{name}.json")
    with open(path, 'w') as f:
        json.dump(json.loads(songs), f)
    return {"status": "saved"}

@app.get("/api/load_playlist/{name}")
def load_playlist(name: str):
    path = os.path.join(PLAYLIST_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return JSONResponse(json.load(f))
    return JSONResponse([], status_code=404)

@app.get("/api/rescan")
def rescan():
    scan_mp3_files()
    return {"status": "rescanned", "count": len(SONG_INDEX)}
