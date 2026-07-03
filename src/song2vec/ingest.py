"""Ingest the Zenodo MySQL dump of the MPD into SQLite, then emit the same
artifacts as the JSON path (playlists.txt + track_meta.json).

Why SQLite: the dump expands to ~35 GB in MySQL. Instead of standing up a
server, we stream the dump straight into a local SQLite file (stdlib only),
keeping only the columns we need, then run two queries to produce:

    data/processed/playlists.txt    one playlist per line, space-separated track URIs
    data/processed/track_meta.json  track_uri -> {"name", "artist"}

Parsing notes:
- mysqldump writes one INSERT statement per line and escapes every newline
  inside a string as "\\n", so a raw newline only ever separates statements.
  => we can safely read the dump line by line.
- Values are single-quoted with backslash escapes; tuples are extended
  (many rows per INSERT). TOKEN_RE tokenises a VALUES blob quote-aware, so
  commas / parens / semicolons inside song titles don't break parsing.

Run:  python -m song2vec.ingest            # uses config.DUMP_FILE
      python -m song2vec.ingest /path/to/dump.sql
"""

import json
import re
import sqlite3
import sys

from tqdm import tqdm

from . import config

# We only need these tables (and, of them, only a few columns each).
#   track(id, name, duration, popularity, explicit, preview_url, uri, album_id)
#   artist(id, name, uri)
#   track_artist1(track_id, artist_id)
#   track_playlist1(track_id, playlist_id)
TARGETS = {"track", "artist", "track_artist1", "track_playlist1"}

INSERT_PREFIX = "INSERT INTO `"

# One token of a VALUES blob: a quoted string (with escapes), NULL, a number,
# or a structural char. Order matters — string alternative must come first.
TOKEN_RE = re.compile(r"'(?:[^'\\]|\\.)*'|NULL|[-+0-9.eE]+|[(),]")

_ESCAPES = {"0": "\0", "n": "\n", "r": "\r", "t": "\t", "b": "\b",
            "Z": "\x1a", "\\": "\\", "'": "'", '"': '"'}
_ESC_RE = re.compile(r"\\(.)")


def _unescape(s: str) -> str:
    if "\\" not in s:
        return s
    return _ESC_RE.sub(lambda m: _ESCAPES.get(m.group(1), m.group(1)), s)


def _fix_text(s):
    """Recover UTF-8 that was stored raw in a latin1 table (we read as latin-1)."""
    if s is None:
        return None
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def parse_tuples(blob: str):
    """Yield each tuple of a VALUES blob as a list (str | None)."""
    row = None
    for m in TOKEN_RE.finditer(blob):
        tok = m.group()
        if tok == "(":
            row = []
        elif tok == ")":
            if row is not None:
                yield row
                row = None
        elif tok == ",":
            continue
        elif row is not None:
            if tok == "NULL":
                row.append(None)
            elif tok[0] == "'":
                row.append(_unescape(tok[1:-1]))
            else:
                row.append(tok)  # numeric, kept as text (we don't use these)


def build_sqlite(dump_path: str, db: sqlite3.Connection) -> None:
    db.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;
        PRAGMA temp_store = MEMORY;
        DROP TABLE IF EXISTS track;
        DROP TABLE IF EXISTS artist;
        DROP TABLE IF EXISTS track_artist;
        DROP TABLE IF EXISTS track_playlist;
        CREATE TABLE track (id TEXT PRIMARY KEY, uri TEXT, name TEXT);
        CREATE TABLE artist (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE track_artist (track_id TEXT, artist_id TEXT);
        CREATE TABLE track_playlist (track_id TEXT, playlist_id TEXT);
        """
    )

    batches = {t: [] for t in TARGETS}
    counts = {t: 0 for t in TARGETS}
    inserts = {
        "track": "INSERT OR IGNORE INTO track VALUES (?,?,?)",
        "artist": "INSERT OR IGNORE INTO artist VALUES (?,?)",
        "track_artist1": "INSERT INTO track_artist VALUES (?,?)",
        "track_playlist1": "INSERT INTO track_playlist VALUES (?,?)",
    }

    def flush(table):
        if batches[table]:
            db.executemany(inserts[table], batches[table])
            counts[table] += len(batches[table])
            batches[table].clear()

    with open(dump_path, "rb") as f:
        for raw in tqdm(f, desc="dump lines", unit="ln"):
            if not raw.startswith(b"INSERT INTO `"):
                continue
            line = raw.decode("latin-1")
            j = line.index("`", len(INSERT_PREFIX))
            table = line[len(INSERT_PREFIX):j]
            if table not in TARGETS:
                continue
            blob = line[line.index(" VALUES ", j) + 8:]
            for row in parse_tuples(blob):
                if table == "track":            # (id, name, dur, pop, expl, prev, uri, album)
                    batches[table].append((row[0], row[6], row[1]))
                elif table == "artist":         # (id, name, uri)
                    batches[table].append((row[0], row[1]))
                else:                           # track_artist1 / track_playlist1: (track_id, other)
                    batches[table].append((row[0], row[1]))
            if len(batches[table]) >= 50_000:
                flush(table)

    for t in TARGETS:
        flush(t)
    db.commit()
    print("Rows ingested:", {t: counts[t] for t in TARGETS})


def emit_track_meta(db: sqlite3.Connection) -> None:
    db.execute("CREATE INDEX IF NOT EXISTS ta_track ON track_artist(track_id)")
    cur = db.execute(
        """
        SELECT t.uri, t.name, a.name
        FROM track t
        LEFT JOIN track_artist ta ON ta.track_id = t.id
        LEFT JOIN artist a ON a.id = ta.artist_id
        WHERE t.uri IS NOT NULL AND t.uri != ''
        GROUP BY t.id
        """
    )
    meta = {}
    for uri, name, artist in tqdm(cur, desc="track_meta"):
        meta[uri] = {"name": _fix_text(name), "artist": _fix_text(artist)}
    with open(config.TRACK_META_FILE, "w") as f:
        json.dump(meta, f)
    print(f"Wrote {len(meta):,} tracks to {config.TRACK_META_FILE}")


def emit_playlists(db: sqlite3.Connection) -> None:
    db.execute("CREATE INDEX IF NOT EXISTS tp_playlist ON track_playlist(playlist_id)")
    cur = db.execute(
        """
        SELECT tp.playlist_id, t.uri
        FROM track_playlist tp
        JOIN track t ON t.id = tp.track_id
        WHERE t.uri IS NOT NULL AND t.uri != ''
        ORDER BY tp.playlist_id
        """
    )
    n_playlists = 0
    current = None
    uris: list[str] = []
    with open(config.PLAYLISTS_FILE, "w") as out:
        for pid, uri in tqdm(cur, desc="playlists"):
            if pid != current:
                if uris:
                    out.write(" ".join(uris) + "\n")
                    n_playlists += 1
                current, uris = pid, []
            uris.append(uri)
        if uris:
            out.write(" ".join(uris) + "\n")
            n_playlists += 1
    print(f"Wrote {n_playlists:,} playlists to {config.PLAYLISTS_FILE}")


def main() -> None:
    dump_path = sys.argv[1] if len(sys.argv) > 1 else str(config.DUMP_FILE)
    db = sqlite3.connect(str(config.SQLITE_FILE))
    print(f"Ingesting {dump_path} -> {config.SQLITE_FILE} ...")
    build_sqlite(dump_path, db)
    emit_track_meta(db)
    emit_playlists(db)
    db.close()
    print("Done. Next: python -m song2vec.train")


if __name__ == "__main__":
    main()
