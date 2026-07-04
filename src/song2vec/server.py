"""FastAPI backend for the PlaylistMaker web app.

Loads the trained song2vec model once at startup and serves same-feel playlists.

Run:  python -m song2vec.server         (http://127.0.0.1:8000)
       or: uvicorn song2vec.server:app --reload
"""

import json
import os
from collections import defaultdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from gensim.models import KeyedVectors, Word2Vec
from pydantic import BaseModel

from . import config

app = FastAPI(title="PlaylistMaker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loaded lazily on first use (model + metadata are several GB).
_state: dict = {}


def _load() -> dict:
    if _state:
        return _state

    # Prefer the slimmed deployment artifacts (KeyedVectors + pruned meta); fall
    # back to the full training model for local dev before `export` is run.
    if config.KV_FILE.exists():
        wv = KeyedVectors.load(str(config.KV_FILE))
        meta_file = config.PRUNED_META_FILE if config.PRUNED_META_FILE.exists() else config.TRACK_META_FILE
    else:
        wv = Word2Vec.load(str(config.MODEL_FILE)).wv
        meta_file = config.TRACK_META_FILE

    vocab = set(wv.index_to_key)
    # Keep metadata only for in-vocab tracks, indexed by lowercased name.
    with open(meta_file) as f:
        full = json.load(f)
    meta = {u: full[u] for u in vocab if u in full}
    del full

    by_name = defaultdict(list)
    for uri, m in meta.items():
        name = (m.get("name") or "").lower()
        if name:
            by_name[name].append(uri)

    _state.update(wv=wv, meta=meta, by_name=by_name)
    return _state


def _resolve(query: str, artist: str | None, st: dict) -> str | None:
    """Resolve a typed song (optionally + artist) to an in-vocab dataset URI.

    A song name maps to many recordings (originals, covers, live versions). We
    pick the most-played one — gensim stores each track's playlist frequency as
    its vocab `count`, so the canonical/popular version wins by default.
    """
    q = query.strip().lower()
    a = artist.strip().lower() if artist else None
    meta, wv = st["meta"], st["wv"]

    def ok(uri):
        return not a or a in (meta[uri].get("artist") or "").lower()

    # 1. exact name matches (indexed); 2. else substring scan over in-vocab tracks
    cands = [u for u in st["by_name"].get(q, []) if ok(u)]
    if not cands:
        cands = [u for u, m in meta.items() if q in (m.get("name") or "").lower() and ok(u)]
    if not cands:
        return None
    return max(cands, key=lambda u: wv.get_vecattr(u, "count"))


class GenerateRequest(BaseModel):
    song: str
    artist: str | None = None
    length: int = 20


@app.get("/api/health")
def health():
    return {"ok": True, "loaded": bool(_state)}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    st = _load()
    wv, meta = st["wv"], st["meta"]

    seed = _resolve(req.song, req.artist, st)
    if not seed:
        return {"error": f"Couldn't find “{req.song}” in the dataset. Try another song or add an artist."}

    n = max(1, min(req.length, 100))
    seed_m = meta[seed]
    # The requested song is track #1, then n-1 nearest neighbours fill the rest.
    tracks = [{
        "name": seed_m.get("name"),
        "artist": seed_m.get("artist"),
        "score": 1.0,
        "uri": seed,
        "seed": True,
    }]
    for uri, score in wv.most_similar(seed, topn=n - 1):
        m = meta.get(uri, {})
        tracks.append({
            "name": m.get("name"),
            "artist": m.get("artist"),
            "score": round(float(score), 3),
            "uri": uri,
        })
    return {
        "seed": {"name": seed_m.get("name"), "artist": seed_m.get("artist")},
        "tracks": tracks,
    }


class SaveTrack(BaseModel):
    name: str | None = None
    artist: str | None = None


class SaveRequest(BaseModel):
    name: str
    tracks: list[SaveTrack]


@app.post("/api/links")
def links(req: SaveRequest):
    """Resolve each track to its current Spotify URL (app-only search, no user
    login). Used by the 'Copy Spotify links' fallback — paste the URLs into a
    new playlist in the Spotify desktop app to fill it instantly.
    """
    from . import spotify

    try:
        out = []
        for t in req.tracks:
            query = " ".join(x for x in (t.name, t.artist) if x)
            hit = spotify.search_track(query) if query else None
            url = None
            if hit:
                track_id = hit["uri"].split(":")[-1]
                url = f"https://open.spotify.com/track/{track_id}"
            out.append({"name": t.name, "artist": t.artist, "url": url})
        return {"tracks": out}
    except KeyError:
        return {"error": "Spotify credentials missing. Add them to .env (see .env.example)."}
    except Exception as e:
        return {"error": f"Spotify error: {type(e).__name__}: {str(e)[:200]}"}


@app.post("/api/save")
def save(req: SaveRequest):
    """Create a real Spotify playlist from the generated tracks.

    Resolves each (name, artist) to a *current* Spotify URI via search, then
    creates the playlist in the user's account. The first /api/save call opens a
    browser for one-time OAuth consent (spotipy caches the token afterwards).
    """
    from . import spotify

    try:
        uris, missed = [], []
        for t in req.tracks:
            query = " ".join(x for x in (t.name, t.artist) if x)
            hit = spotify.search_track(query) if query else None
            (uris.append(hit["uri"]) if hit else missed.append(query))

        if not uris:
            return {"error": "None of the tracks could be matched on Spotify."}

        url = spotify.create_playlist(req.name, uris, public=False)
        return {"url": url, "added": len(uris), "missed": len(missed)}
    except KeyError:
        return {"error": "Spotify credentials missing. Add them to .env (see .env.example)."}
    except Exception as e:  # spotipy/auth/network errors
        return {"error": f"Spotify error: {type(e).__name__}: {str(e)[:200]}"}


# Serve the built frontend (web/dist) from the same service, so the whole app is
# one deployable at one URL. Mounted last so /api/* routes take precedence.
_DIST = config.ROOT / "web" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")


def main():
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8008))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
