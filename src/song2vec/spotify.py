"""Spotify Web API helpers: resolve a song name to a track URI, and optionally
write a generated playlist back to the user's account.

Requires a Spotify developer app. Copy .env.example -> .env and fill it in.

- search_track:    app-only auth (Client Credentials) — no user login needed.
- create_playlist: user auth (OAuth) — opens a browser the first time to log in.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _client(user_auth: bool = False):
    import spotipy

    if user_auth:
        # Spotify's 2025 security migration requires PKCE for the auth-code flow,
        # so we use SpotifyPKCE (no client secret in the user-auth exchange).
        from spotipy.oauth2 import SpotifyPKCE

        return spotipy.Spotify(
            auth_manager=SpotifyPKCE(
                client_id=os.environ["SPOTIPY_CLIENT_ID"],
                redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8890/callback"),
                scope="playlist-modify-private playlist-modify-public",
                open_browser=True,
            )
        )

    from spotipy.oauth2 import SpotifyClientCredentials

    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=os.environ["SPOTIPY_CLIENT_ID"],
            client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        )
    )


def search_track(query: str) -> dict | None:
    """Resolve a free-text song name to the best-matching Spotify track."""
    sp = _client()
    items = sp.search(q=query, type="track", limit=1)["tracks"]["items"]
    if not items:
        return None
    t = items[0]
    return {"uri": t["uri"], "name": t["name"], "artist": t["artists"][0]["name"]}


def create_playlist(name: str, track_uris: list[str], public: bool = False) -> str:
    """Create a playlist in the current user's account and add the tracks. Returns its URL."""
    sp = _client(user_auth=True)
    user_id = sp.me()["id"]
    pl = sp.user_playlist_create(user_id, name, public=public)
    for i in range(0, len(track_uris), 100):  # API caps adds at 100 per call
        sp.playlist_add_items(pl["id"], track_uris[i : i + 100])
    return pl["external_urls"]["spotify"]
