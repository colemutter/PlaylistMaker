"""Export a slimmed model for deployment.

The training model is ~3.4 GB on disk and ~5-8 GB in RAM (it keeps the syn1neg
training matrix and 3.3M vectors). For hosting we don't need any of that. This:

  1. keeps only the top-N most-played tracks (gensim stores vocab sorted by
     frequency, so these are just the first N),
  2. saves them as plain KeyedVectors — no syn1neg, half the size,
  3. writes metadata limited to those tracks.

Outputs (a few hundred MB total, cheap to ship in a container):
    models/song2vec.kv (+ .vectors.npy)
    data/processed/meta.min.json

Run:  python -m song2vec.export           # uses config.EXPORT_TOP_N
      python -m song2vec.export 300000    # custom N
"""

import json
import sys

from gensim.models import KeyedVectors, Word2Vec

from . import config


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else config.EXPORT_TOP_N

    print(f"Loading full model {config.MODEL_FILE} ...")
    wv = Word2Vec.load(str(config.MODEL_FILE)).wv
    n = min(n, len(wv))
    keys = wv.index_to_key[:n]  # already sorted by descending playlist frequency

    print(f"Keeping top {n:,} of {len(wv):,} tracks ...")
    slim = KeyedVectors(vector_size=wv.vector_size)
    slim.add_vectors(keys, wv.vectors[:n])
    for k in keys:  # preserve counts so the server can pick the most-played version
        slim.set_vecattr(k, "count", int(wv.get_vecattr(k, "count")))
    slim.save(str(config.KV_FILE))
    print(f"Saved KeyedVectors -> {config.KV_FILE}")

    print("Pruning metadata ...")
    with open(config.TRACK_META_FILE) as f:
        full = json.load(f)
    pruned = {k: full[k] for k in keys if k in full}
    with open(config.PRUNED_META_FILE, "w") as f:
        json.dump(pruned, f)
    print(f"Saved {len(pruned):,} track metadata rows -> {config.PRUNED_META_FILE}")
    print("Done. The server auto-uses these when present.")


if __name__ == "__main__":
    main()
