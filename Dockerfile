FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

COPY src/ ./src/
COPY data/processed/ ./data/processed/

CMD ["uv", "run", "src/training_pipeline/train.py"]
