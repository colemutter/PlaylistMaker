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

# Zenodo SQL-dump ingestion path (alternative to the JSON-slice path)
DUMP_FILE = RAW_DIR / "spotifydbdump.sql"             # raw MySQL dump from the Zenodo mirror
SQLITE_FILE = PROCESSED_DIR / "mpd.sqlite"            # local scratch DB built from the dump

# Deployment artifacts — a slimmed model + metadata for hosting (see export.py).
KV_FILE = MODELS_DIR / "song2vec.kv"                  # pruned KeyedVectors (no syn1neg), for serving
PRUNED_META_FILE = PROCESSED_DIR / "meta.min.json"    # metadata limited to the pruned vocab
EXPORT_TOP_N = 500_000                                 # keep the N most-played tracks

# Word2Vec hyperparameters (tune later)
VECTOR_SIZE = 128   # dimensionality of each song vector
WINDOW = 10         # playlist order is weak, so a wide context window works well
MIN_COUNT = 5       # ignore songs that appear in fewer than this many playlists
EPOCHS = 5
SG = 1              # 1 = skip-gram (better here), 0 = CBOW
NEGATIVE = 10       # negative sampling
WORKERS = 12        # training threads (14-core machine; leave headroom for the feeder)

for _d in (RAW_DIR, PROCESSED_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
