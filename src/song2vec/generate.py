"""Generate a 'same-feel' playlist from a seed song.

Given a seed track, returns its nearest neighbours in the embedding space — the
songs that most often share playlists with it, i.e. the closest in 'feel'.

Run:
    python -m song2vec.generate "spotify:track:..." -n 20
    python -m song2vec.generate "Bohemian Rhapsody" -n 20   # local name search
"""

import argparse
import json

from gensim.models import Word2Vec

from . import config


def load():
    model = Word2Vec.load(str(config.MODEL_FILE))
    with open(config.TRACK_META_FILE) as f:
        meta = json.load(f)
    return model, meta


def label(uri: str, meta: dict) -> str:
    m = meta.get(uri)
    return f"{m['name']} — {m['artist']}" if m else uri


def find_uri_by_name(query: str, meta: dict) -> str | None:
    """Naive local lookup: first metadata entry whose name contains the query."""
    q = query.lower()
    for uri, m in meta.items():
        if q in m["name"].lower():
            return uri
    return None


def generate(seed_uri: str, length: int, model, meta) -> list[tuple[str, float]] | None:
    if seed_uri not in model.wv:
        return None
    return model.wv.most_similar(seed_uri, topn=length)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a same-feel playlist from a seed song.")
    ap.add_argument("seed", help="A track URI (spotify:track:...) or a song name to search locally")
    ap.add_argument("-n", "--length", type=int, default=20, help="Playlist length")
    args = ap.parse_args()

    model, meta = load()

    seed_uri = args.seed if args.seed.startswith("spotify:track:") else find_uri_by_name(args.seed, meta)
    if not seed_uri:
        raise SystemExit(f"Could not find a seed track for {args.seed!r}.")

    print(f"Seed: {label(seed_uri, meta)}\n")
    result = generate(seed_uri, args.length, model, meta)
    if result is None:
        raise SystemExit("Seed is not in the trained vocabulary (too rare, or outside the dataset).")

    for i, (uri, score) in enumerate(result, 1):
        print(f"{i:2}. {label(uri, meta)}   ({score:.3f})")


if __name__ == "__main__":
    main()
