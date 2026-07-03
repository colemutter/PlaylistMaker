"""Central paths and hyperparameters for the song2vec pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"              # unzipped MPD slices: mpd.slice.*.json
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = ROOT / "models"

# Pipeline artifacts
PLAYLISTS_FILE = PROCESSED_DIR / "playlists.txt"      # one playlist per line, space-separated track URIs
TRACK_META_FILE = PROCESSED_DIR / "track_meta.json"   # track_uri -> {"name", "artist"}
MODEL_FILE = MODELS_DIR / "song2vec.model"

# Word2Vec hyperparameters (tune later)
VECTOR_SIZE = 128   # dimensionality of each song vector
WINDOW = 10         # playlist order is weak, so a wide context window works well
MIN_COUNT = 5       # ignore songs that appear in fewer than this many playlists
EPOCHS = 5
SG = 1              # 1 = skip-gram (better here), 0 = CBOW
NEGATIVE = 10       # negative sampling
WORKERS = 8         # training threads

for _d in (RAW_DIR, PROCESSED_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
