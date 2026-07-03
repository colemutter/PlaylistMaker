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


def find_uri_by_name(query: str, meta: dict, model=None, artist: str | None = None) -> str | None:
    """Resolve a song name to an in-dataset track URI.

    The Spotify API's current URI for a song usually differs from the 2017
    dataset's URI, so we match by name (and optional artist) within the dataset,
    preferring an exact name match and a URI that is actually in the trained
    vocabulary (so generate() can use it).
    """
    q = query.lower()
    a = artist.lower() if artist else None
    exact, partial = [], []
    for uri, m in meta.items():
        name = (m.get("name") or "").lower()
        if not name:
            continue
        if a and a not in (m.get("artist") or "").lower():
            continue
        if name == q:
            exact.append(uri)
        elif q in name:
            partial.append(uri)

    def pick(cands):
        if not cands:
            return None
        if model is not None:
            in_vocab = [u for u in cands if u in model.wv]
            if in_vocab:
                return in_vocab[0]
        return cands[0]

    return pick(exact) or pick(partial)


def generate(seed_uri: str, length: int, model, meta) -> list[tuple[str, float]] | None:
    if seed_uri not in model.wv:
        return None
    return model.wv.most_similar(seed_uri, topn=length)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a same-feel playlist from a seed song.")
    ap.add_argument("seed", help="A track URI (spotify:track:...) or a song name to search locally")
    ap.add_argument("-n", "--length", type=int, default=20, help="Playlist length")
    ap.add_argument("-a", "--artist", default=None, help="Optional artist hint to disambiguate the seed")
    args = ap.parse_args()

    model, meta = load()

    if args.seed.startswith("spotify:track:"):
        seed_uri = args.seed
    else:
        seed_uri = find_uri_by_name(args.seed, meta, model=model, artist=args.artist)
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
