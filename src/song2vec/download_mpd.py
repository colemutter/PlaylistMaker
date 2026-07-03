"""Prepare the Spotify Million Playlist Dataset (MPD).

The MPD is not available via a direct anonymous URL — it is distributed through
AIcrowd and requires a free account:

    https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge

Download `spotify_million_playlist_dataset.zip` (~5.4 GB), then run:

    python -m song2vec.download_mpd /path/to/spotify_million_playlist_dataset.zip

This extracts the `mpd.slice.*.json` files into data/raw/ (there are 1,000 of
them, 1,000 playlists each). You can also just unzip manually into data/raw/.
"""

import sys
import zipfile
from pathlib import Path

from . import config


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    zip_path = sys.argv[1]
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for member in z.namelist():
            name = Path(member).name
            if name.startswith("mpd.slice.") and name.endswith(".json"):
                with z.open(member) as src, open(config.RAW_DIR / name, "wb") as dst:
                    dst.write(src.read())
                n += 1

    if n == 0:
        raise SystemExit("No mpd.slice.*.json files found in that zip.")
    print(f"Extracted {n} slices into {config.RAW_DIR}")


if __name__ == "__main__":
    main()
