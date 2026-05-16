# hevy-fti-predictor

> *your gym data, but make it machine learning*

A fully automated MLOps pipeline that pulls your workout history from [Hevy](https://hevy.com), engineers 30+ features from raw lift data, and trains models to predict future training loads — all versioned, containerized, and running on CI/CD.

**Stack:** Python · FastAPI · DVC · MLflow (DagsHub) · Docker · Cloud Run · GitHub Actions · GCS

## Pipeline

![Project Overview](docs/images/project_overview.png)


**Features computed:** rolling volume per muscle group, days since last exercise, volume trends, session history, global workload (7d/28d), workout frequency, temporal features - 16 feature columns.

## Inference

The trained model is served via a **FastAPI** app containerized and deployed to **Google Cloud Run**.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/exercises` | GET | List available exercises from history |
| `/predict` | POST | Predict volume for a single exercise |
| `/predict/batch` | POST | Predict volume for multiple exercises at once |

**Deploy:**

```bash
./scripts/setup-gcp.sh        # one-time GCP setup
./scripts/set-permissions.sh  # one-time IAM permissions
./scripts/deploy.sh           # build & deploy
```

See [docs/inference.md](docs/inference.md) for the full guide.

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

## Environment Variables

Create a `.env` file from the template:

```bash
cp example.env .env
```

| Variable | Required for | Description |
|----------|--------------|-------------|
| `HEVY_API_KEY` | Data fetch | Hevy API key |
| `DAGSHUB_TOKEN` | Training | DagsHub access token ([get one here](https://dagshub.com/user/settings/tokens)) |
| `DAGSHUB_REPO_OWNER` | Training | Your DagsHub username |
| `DAGSHUB_REPO_NAME` | Training | Repository name on DagsHub |

## Docker

Two Dockerfiles are provided:

| File | Purpose |
|------|---------|
| `Dockerfile` | Training pipeline |
| `Dockerfile.serve` | FastAPI inference server |

**Training:**

```bash
docker build -t hevy-fti-predictor:train .
docker run --rm \
  -e DAGSHUB_TOKEN=<your_token> \
  -e DAGSHUB_REPO_OWNER=jackra1n \
  -e DAGSHUB_REPO_NAME=hevy-fti-predictor \
  hevy-fti-predictor:train
```

**Inference (local):**

```bash
docker build -f Dockerfile.serve -t hevy-fti-predictor:inference .
docker run --rm -p 8080:8080 \
  -e DAGSHUB_TOKEN=<your_token> \
  -e DAGSHUB_REPO_OWNER=jackra1n \
  -e DAGSHUB_REPO_NAME=hevy-fti-predictor \
  hevy-fti-predictor:inference
```

## CI/CD

Two GitHub Actions workflows run the FTI pipeline:

| Workflow | File | Trigger | What it does |
|----------|------|---------|--------------|
| **Update Data** | `.github/workflows/update-data.yml` | Daily at 06:00 UTC | Fetches Hevy workouts, computes features, pushes data to GCS via DVC |
| **Train Model** | `.github/workflows/train.yml` | After Update Data succeeds | Pulls latest data, builds Docker image, runs training, logs experiments to DagsHub MLflow |

A third workflow handles inference deployment:

| Workflow | File | Trigger | What it does |
|----------|------|---------|--------------|
| **Deploy Inference** | `.github/workflows/deploy.yml` | After Train Model succeeds | Pulls latest feature store, builds inference Docker image, deploys to Cloud Run |

Requires these **repository secrets** (Settings → Secrets and variables → Secrets):

| Secret | Description |
|--------|-------------|
| `HEVY_API_KEY` | Hevy API key |
| `GCP_PROJECT_ID` | GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name |
| `GCP_SERVICE_ACCOUNT` | SA email (`github-actions@<PROJECT>.iam.gserviceaccount.com`) |
| `DAGSHUB_TOKEN` | DagsHub access token |

And these **repository variables** (Settings → Secrets and variables → Variables):

| Variable | Description |
|----------|-------------|
| `DAGSHUB_REPO_OWNER` | Your DagsHub username |
| `DAGSHUB_REPO_NAME` | Repository name on DagsHub |

See [docs/gcs.md](docs/gcs.md) for GCP setup instructions.

## Tools

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Python environment & dependencies |
| [mise](https://mise.jdx.dev/) | Global tool versioning (gcloud, pipx) |
| [DVC](https://dvc.org/) | Data version control |
| [pipx](https://pipx.pypa.io/) | Isolated install for `dvc[gs]` |
| [gcloud](https://cloud.google.com/sdk/gcloud) | GCS authentication |
