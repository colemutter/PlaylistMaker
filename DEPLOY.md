# Deploying PlaylistMaker to Fly.io

One container serves both the API and the frontend. It runs the **slimmed** model
(~1 GB RAM), so a 2 GB always-on Fly machine (~$5–6/mo) handles it comfortably.

## 0. Build the deploy artifacts (once, and after any model/UI change)

```bash
# slim model + pruned metadata  -> models/song2vec.kv*, data/processed/meta.min.json
python -m song2vec.export

# production frontend            -> web/dist
cd web && npm run build && cd ..
```

These are baked into the image (see `Dockerfile`). The 10 GB dump, SQLite, full
model, and node_modules are excluded via `.dockerignore`.

## 1. Install flyctl and log in

```bash
brew install flyctl        # macOS
fly auth signup            # or: fly auth login
```

## 2. Create the app

`fly.toml` is already committed. Point it at a unique app name + a region near you:

```bash
fly launch --no-deploy
# - reuse the existing fly.toml / Dockerfile when prompted
# - pick a unique app name (updates `app` in fly.toml)
# - pick a region (e.g. sea, sjc, ord, iad, lhr)
```

## 3. Set Spotify credentials as secrets

These power the "Find on Spotify" links (app-only search — no user login needed):

```bash
fly secrets set SPOTIPY_CLIENT_ID=xxxx SPOTIPY_CLIENT_SECRET=yyyy
```

(They're injected as env vars — never baked into the image.)

## 4. Deploy

```bash
fly deploy          # remote builder builds the amd64 image and ships it
fly open            # opens the live URL
fly logs            # watch startup / requests
fly status          # machine state
```

First boot loads the model in a few seconds; the `/api/health` check waits for it.

## Updating

After changing the model or UI, re-run step 0, then `fly deploy`.

## Notes

- `min_machines_running = 1` + `auto_stop_machines = false` keep it warm (no
  cold-start model reloads) — the right call for a portfolio link.
- Memory: uses ~1.1 GB; bump with `fly scale memory 4096` only if you raise
  `EXPORT_TOP_N` a lot.
- "Save to Spotify" (server-side playlist creation) is blocked by Spotify's
  Development-Mode policy; the "Copy Spotify links" fallback works in production.
