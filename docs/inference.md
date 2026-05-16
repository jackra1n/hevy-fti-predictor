# Inference

The trained model is served via a **FastAPI** application, containerized with Docker, and deployed to **Google Cloud Run**.

## Architecture

```
User Request
    ↓
Cloud Run (FastAPI)
    ↓
MLflow Model Registry (DagsHub)  ← loads model at first request
    ↓
Prediction + feature engineering
    ↓
JSON Response
```

The model is loaded **lazily** on the first prediction request and kept in memory for the lifetime of the container instance. Cloud Run is configured with `--min-instances 1` so one instance is always warm, avoiding cold-start latency.

## API Endpoints

### `GET /health`

Health check. Returns immediately.

**Response:**
```json
{
  "status": "ok"
}
```

### `GET /exercises`

Lists all exercises that appear in the workout history, sorted by most recently trained.

**Response:**
```json
[
  {
    "name": "Bench Press (Barbell)",
    "last_trained": "2026-04-29"
  }
]
```

### `POST /predict`

Predicts the total volume for a single exercise's next session.

**Request:**
```json
{
  "exercise_name": "Bench Press (Barbell)",
  "planned_time": "2026-05-16T18:00:00Z"
}
```

`planned_time` is optional; defaults to now.

**Response:**
```json
{
  "exercise_name": "Bench Press (Barbell)",
  "predicted_volume_kg": 1832.2,
  "estimated_weight_kg": 59.1,
  "estimated_sets": 4,
  "estimated_reps_per_set": 7.8,
  "last_session_date": "2026-04-29",
  "last_session_volume_kg": 1910.0,
  "features_used": { ... },
  "model_version": "hevy-fti-model:latest"
}
```

### `POST /predict/batch`

Predicts volumes for multiple exercises in a single request. Useful for demoing a full workout plan.

**Request:**
```json
{
  "exercises": [
    "Bench Press (Barbell)",
    "Hammer Curl (Dumbbell)",
    "Pull Up"
  ],
  "planned_time": "2026-05-16T18:00:00Z"
}
```

**Response:**
```json
{
  "predictions": [
    { "exercise_name": "Bench Press (Barbell)", "predicted_volume_kg": 1832.2, ... },
    { "exercise_name": "Hammer Curl (Dumbbell)", "predicted_volume_kg": 391.0, ... },
    { "exercise_name": "Pull Up", "predicted_volume_kg": 0.0, ... }
  ]
}
```

Partial failures are allowed: if one exercise has no history, it is skipped and the rest are returned.

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
   - `--min-instances 1` (keeps one instance warm)
   - `--max-instances 1` (limits cost)
   - `--memory 1Gi`
   - `--allow-unauthenticated` (public access)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DAGSHUB_TOKEN` | Yes | DagsHub personal access token |
| `DAGSHUB_REPO_OWNER` | Yes | DagsHub username |
| `DAGSHUB_REPO_NAME` | Yes | Repository name on DagsHub |
| `MLFLOW_MODEL_URI` | No | Model registry URI (default: `models:/hevy-fti-model/latest`) |
| `HISTORY_CSV_PATH` | No | Path to workout history CSV (default: `data/processed/workouts_exercises.csv`) |

## Performance Notes

- **First request per instance:** ~5-10 seconds (model download from DagsHub MLflow)
- **Subsequent requests:** ~100-300 ms
- **Cold starts avoided:** `--min-instances 1` keeps one container always running
- **Model caching:** The sklearn pipeline is cached in memory via `ModelProvider`

## Files

| File | Purpose |
|------|---------|
| `src/inference_pipeline/api.py` | FastAPI application |
| `src/inference_pipeline/feature_provider.py` | Feature engineering for inference |
| `src/inference_pipeline/inference.py` | Model loading and prediction helpers |
| `Dockerfile.serve` | Inference container definition |
| `cloudbuild.yaml` | Cloud Build configuration |
| `scripts/setup-gcp.sh` | One-time GCP setup |
| `scripts/set-permissions.sh` | IAM permission setup |
| `scripts/deploy.sh` | Build and deploy script |
