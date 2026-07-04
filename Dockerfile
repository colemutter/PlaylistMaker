FROM python:3.12-slim

WORKDIR /app

# Install dependencies via an editable install so the package stays at
# /app/src and config.ROOT resolves to /app (where models/, data/, web/ live).
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .

# Slimmed model + pruned metadata (built locally: `python -m song2vec.export`)
COPY models/song2vec.kv models/song2vec.kv.vectors.npy ./models/
COPY data/processed/meta.min.json ./data/processed/meta.min.json

# Prebuilt frontend (built locally: `cd web && npm run build`)
COPY web/dist ./web/dist

ENV HOST=0.0.0.0 PORT=8080
EXPOSE 8080
CMD ["python", "-m", "song2vec.server"]
