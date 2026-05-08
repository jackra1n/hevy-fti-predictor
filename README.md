# hevy-fti-predictor

MLOps university project that fetches workout data from the [Hevy](https://hevy.com) API and builds a versioned feature store for downstream ML tasks.

## Pipeline

```
Hevy API → fetch.py → data/raw/ + data/processed/workouts_exercises.csv
                           ↓
               feature_engineering.py
                           ↓
               data/processed/features_*.csv
                           ↓
                    train.py
                           ↓
               models/ + DagsHub MLflow
```

**Features computed:** rolling volume per muscle group, days since last exercise, volume trends, session history, global workload (7d/28d), workout frequency, temporal features — 30 columns total.

## Quickstart

```bash
# Install tools
mise install

# Install Python dependencies
uv sync

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login

# Pull data from DVC remote
dvc pull

# Set your Hevy API key
echo "HEVY_API_KEY=<your_key>" > .env

# Run
uv run src/feature_pipeline/fetch.py
uv run src/feature_pipeline/feature_engineering.py
uv run src/training_pipeline/train.py
```

## Data Versioning

[DVC](https://dvc.org/) tracks `data/raw/` and `data/processed/` with content-addressed storage. Raw data lives on Google Cloud Storage (`gs://hevy-fti-predictor/dvc-store`); Git only tracks lightweight `.dvc` metafiles.

```bash
dvc add data/raw/ data/processed/   # track after new data
dvc push                             # upload to GCS
dvc pull                             # download from GCS
```

## Google Cloud

Data is stored in a GCS bucket. [More info →](docs/gcs.md)

## CI/CD

A GitHub Actions workflow (`.github/workflows/update-data.yml`) runs daily to fetch new Hevy workouts, compute features, and push updated data to GCS.

Requires these **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `HEVY_API_KEY` | Hevy API key |
| `GCP_PROJECT_ID` | GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name |
| `GCP_SERVICE_ACCOUNT` | SA email (`github-actions@<PROJECT>.iam.gserviceaccount.com`) |

See [docs/gcs.md](docs/gcs.md) for setup instructions.

## Tools

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Python environment & dependencies |
| [mise](https://mise.jdx.dev/) | Global tool versioning (gcloud, pipx) |
| [DVC](https://dvc.org/) | Data version control |
| [pipx](https://pipx.pypa.io/) | Isolated install for `dvc[gs]` |
| [gcloud](https://cloud.google.com/sdk/gcloud) | GCS authentication |
