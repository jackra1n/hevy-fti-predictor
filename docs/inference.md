# Inference

The trained model is served via a **FastAPI** application, containerized with Docker, and deployed to **Google Cloud Run**.

## Architecture

```
User Request
    ↓
Cloud Run (FastAPI)
    ↓
Pre-computed Feature Store (features_*.csv)  ← loaded at startup
    ↓
Phantom feature computation (O(1))
    ↓
MLflow Model Registry (DagsHub)  ← loaded at startup
    ↓
Prediction
    ↓
JSON Response
```

The model and pre-computed feature store are loaded in **background threads at import time**, so they are ready before the first request arrives. Cloud Run is configured with `--min-instances 1` so one instance is always warm, avoiding cold-start latency.

This follows the FTI architecture: the **Feature Pipeline** (GitHub Actions) computes features and pushes them to GCS via DVC. The **Inference Pipeline** pulls the latest `features_*.csv` at build time (baked into the Docker image) and derives phantom-row features directly from the cached store - never re-running the full feature-engineering pipeline.

## API

See [api.md](api.md) for the full API reference (endpoints, request/response schemas, and curl examples).

## Local Testing

```bash
# Build the inference image
docker build -f Dockerfile.serve -t hevy-inference:latest .

# Run locally
docker run -p 8080:8080 \
  -e DAGSHUB_TOKEN=<your_token> \
  -e DAGSHUB_REPO_OWNER=jackra1n \
  -e DAGSHUB_REPO_NAME=hevy-fti-predictor \
  hevy-inference:latest

# Test
curl http://localhost:8080/health
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"exercise_name":"Bench Press (Barbell)"}'
```

## Deployment

### Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated
- DagsHub token

### One-time setup

```bash
./scripts/setup-gcp.sh        # enables APIs, creates Artifact Registry repo
./scripts/set-permissions.sh  # grants Cloud Build service account permissions
```

### Deploy

```bash
./scripts/deploy.sh
```

This script:
1. Builds the image via Google Cloud Build (using `cloudbuild.yaml` + `Dockerfile.serve`)
2. Pushes to Artifact Registry
3. Deploys to Cloud Run with:
   - `--max-instances 1` (limits cost)
   - `--memory 1Gi`
   - `--cpu 2`
   - `--allow-unauthenticated` (public access)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DAGSHUB_TOKEN` | Yes | DagsHub personal access token |
| `DAGSHUB_REPO_OWNER` | Yes | DagsHub username |
| `DAGSHUB_REPO_NAME` | Yes | Repository name on DagsHub |
| `MLFLOW_MODEL_URI` | No | Model registry URI (default: `models:/hevy-fti-model/latest`) |
| `PROCESSED_DIR` | No | Directory containing the feature store CSV (default: `data/processed`) |

## Files

| File | Purpose |
|------|---------|
| `src/inference_pipeline/api.py` | FastAPI application |
| `src/inference_pipeline/feature_store.py` | Loads and caches pre-computed feature CSV from the feature store |
| `src/inference_pipeline/feature_provider.py` | Builds phantom-row features from cached store (O(1) lookups) |
| `src/inference_pipeline/inference.py` | Model loading and prediction helpers |
| `Dockerfile.serve` | Inference container definition (copies `data/processed/` at build time) |
| `cloudbuild.yaml` | Cloud Build configuration |
| `scripts/setup-gcp.sh` | One-time GCP setup |
| `scripts/set-permissions.sh` | IAM permission setup |
| `scripts/deploy.sh` | Build and deploy script |
