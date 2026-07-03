"""Turn raw MPD JSON slices into a training corpus + a track-metadata lookup.

Each MPD slice looks like:
    {"playlists": [
        {"name": ..., "tracks": [
            {"track_uri": "spotify:track:...", "track_name": ..., "artist_name": ...}, ...]},
        ...]}

Outputs:
    data/processed/playlists.txt    one playlist per line, space-separated track URIs
    data/processed/track_meta.json  track_uri -> {"name", "artist"}

Run:  python -m song2vec.parse
"""

import glob
import json

from tqdm import tqdm

from . import config


def slice_files() -> list[str]:
    return sorted(glob.glob(str(config.RAW_DIR / "mpd.slice.*.json")))


def main() -> None:
    files = slice_files()
    if not files:
        raise SystemExit(
            f"No MPD slices found in {config.RAW_DIR}.\n"
            "Download the dataset first (see `python -m song2vec.download_mpd`)."
        )

    meta: dict[str, dict[str, str]] = {}
    n_playlists = 0

    with open(config.PLAYLISTS_FILE, "w") as out:
        for path in tqdm(files, desc="slices"):
            with open(path) as f:
                data = json.load(f)
            for pl in data["playlists"]:
                uris = []
                for t in pl["tracks"]:
                    uri = t["track_uri"]
                    uris.append(uri)
                    if uri not in meta:
                        meta[uri] = {"name": t["track_name"], "artist": t["artist_name"]}
                if uris:
                    out.write(" ".join(uris) + "\n")
                    n_playlists += 1

    with open(config.TRACK_META_FILE, "w") as f:
        json.dump(meta, f)

    print(f"Wrote {n_playlists:,} playlists and {len(meta):,} unique tracks.")


if __name__ == "__main__":
    main()
