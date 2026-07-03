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

```bash
# 1. Get the data (needs a free AIcrowd account — see the link above)
python -m song2vec.download_mpd /path/to/spotify_million_playlist_dataset.zip

# 2. Build the training corpus + track metadata
python -m song2vec.parse

# 3. Train the embeddings
python -m song2vec.train

# 4. Generate a playlist from a seed song
python -m song2vec.generate "spotify:track:..." -n 20
python -m song2vec.generate "Mr. Brightside" -n 20   # local name search
```

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
  download_mpd.py  extract MPD slices into data/raw/
  parse.py         MPD slices -> playlists.txt + track_meta.json
  train.py         playlists.txt -> models/song2vec.model
  generate.py      seed song -> nearest-neighbour playlist
  spotify.py       name resolution + playlist creation (Spotify Web API)
data/raw/          MPD slices (gitignored)
data/processed/    corpus + metadata (gitignored)
models/            trained model (gitignored)
```
