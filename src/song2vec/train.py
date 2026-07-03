"""Train song2vec embeddings from the playlist corpus.

Treats each playlist as a 'sentence' and each track URI as a 'word', so songs
that co-occur in playlists end up with nearby vectors.

Run:  python -m song2vec.train
"""

import logging

from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence

from . import config


def main() -> None:
    if not config.PLAYLISTS_FILE.exists():
        raise SystemExit(
            f"Missing {config.PLAYLISTS_FILE}. Run ingest (or parse) first."
        )

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO
    )
    print("Training Word2Vec on playlists ...")
    model = Word2Vec(
        sentences=LineSentence(str(config.PLAYLISTS_FILE)),
        vector_size=config.VECTOR_SIZE,
        window=config.WINDOW,
        min_count=config.MIN_COUNT,
        sg=config.SG,
        negative=config.NEGATIVE,
        epochs=config.EPOCHS,
        workers=config.WORKERS,
    )
    model.save(str(config.MODEL_FILE))
    print(f"Saved {len(model.wv):,} song vectors to {config.MODEL_FILE}")


if __name__ == "__main__":
    main()
