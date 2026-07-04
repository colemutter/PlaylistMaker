# PlaylistMaker — song2vec

A [word2vec](https://en.wikipedia.org/wiki/Word2vec)-style embedding model for **songs**.
Instead of learning word vectors from sentences, it learns **song vectors from playlists**:
each playlist is a "sentence" and each song is a "word", so songs that frequently share
playlists end up close together in a high-dimensional space.

**Goal:** give it the name of a song + a length, and it generates a playlist with the
same *feel* as that song — by finding its nearest neighbours in the embedding space.

## How it works

| word2vec | song2vec |
|----------|----------|
| sentence | playlist |
| word     | song (Spotify track URI) |
| nearby words are related | nearby songs share a vibe |

Trained on the [Spotify Million Playlist Dataset](https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge)
(1M playlists, ~2.2M unique songs).

## Setup

```bash
# Create the environment (Python 3.12; gensim has no wheels for 3.14 yet)
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

## Pipeline

The official AIcrowd/Spotify download is closed (you must email Spotify Research).
This project instead ingests the **Zenodo mirror** — a MySQL dump of the same 1M
playlists ([record 5002584](https://zenodo.org/records/5002584), 10.7 GB).

```bash
# 1. Download the dump (resumable)
curl -L -C - "https://zenodo.org/records/5002584/files/spotifydbdumpshare.sql?download=1" \
     -o data/raw/spotifydbdump.sql
# optional integrity check — expected MD5: 3549b42e207a76ba5c20e650f1cd044e
md5 data/raw/spotifydbdump.sql

# 2. Ingest the dump -> local SQLite -> playlists.txt + track_meta.json
#    (streams the dump; no MySQL server needed)
python -m song2vec.ingest

# 3. Train the embeddings
python -m song2vec.train

# 4. Generate a playlist from a seed song
python -m song2vec.generate "spotify:track:..." -n 20
python -m song2vec.generate "Mr. Brightside" -n 20   # local name search
```

<details>
<summary>Alternative: raw JSON slices (if you obtain the original MPD)</summary>

```bash
python -m song2vec.download_mpd /path/to/spotify_million_playlist_dataset.zip
python -m song2vec.parse        # JSON slices -> playlists.txt + track_meta.json
```
</details>

## Web app

A React/Vite frontend (purple animated sound-wave background) on a FastAPI backend
that serves same-feel playlists from the trained model.

```bash
# 1. Backend — loads the model on the first request (port 8008)
python -m song2vec.server

# 2. Frontend — in another terminal (port 5180)
cd web
npm install       # first time only
npm run dev
```

Then open **http://localhost:5180**, type a song (optionally an artist to disambiguate),
pick a length, and hit *Generate*.

- Backend endpoint: `POST /api/generate  {song, artist?, length}` → `{seed, tracks[]}`
- Seed resolution matches by name within the dataset and picks the **most-played**
  version (gensim vocab `count`), since the Spotify API's current track URIs differ
  from the 2017 dataset's. Add an artist to force a specific recording.
- Ports: backend 8008, frontend 5180 (8000/5173 are often taken by other projects).

Files: [`src/song2vec/server.py`](src/song2vec/server.py), [`web/`](web/).

## Spotify API (for the app layer)

To resolve real song names and write playlists back to your account, create a Spotify
developer app, then:

```bash
cp .env.example .env   # and fill in your client id/secret
```

See [`src/song2vec/spotify.py`](src/song2vec/spotify.py) for `search_track()` and `create_playlist()`.

## Layout

```
src/song2vec/
  config.py        paths + Word2Vec hyperparameters
  ingest.py        Zenodo SQL dump -> SQLite -> playlists.txt + track_meta.json
  download_mpd.py  extract MPD JSON slices into data/raw/ (alternative path)
  parse.py         MPD JSON slices -> playlists.txt + track_meta.json (alternative path)
  train.py         playlists.txt -> models/song2vec.model
  generate.py      seed song -> nearest-neighbour playlist
  spotify.py       name resolution + playlist creation (Spotify Web API)
data/raw/          MPD slices (gitignored)
data/processed/    corpus + metadata (gitignored)
models/            trained model (gitignored)
```
