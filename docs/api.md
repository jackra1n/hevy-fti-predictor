# Predictor API

> Base URL: your Cloud Run deployment (or `http://localhost:8080` locally)

## Endpoints

### `GET /health`

Check if the service is alive.

```bash
curl http://localhost:8080/health
```

```json
{ "status": "ok", "model_ready": true, "feature_store_ready": true }
```

### `GET /exercises`

List all exercises in your workout history, sorted by most recently trained.

```bash
curl http://localhost:8080/exercises
```

### `POST /predict`

Predict next-session volume for a single exercise.

| Field           | Type     | Required | Description                  |
|-----------------|----------|----------|------------------------------|
| `exercise_name` | string   | yes      | Exact exercise name (case-sensitive) |
| `planned_time`  | datetime | no       | Future session time (defaults to now) |

```bash
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"exercise_name": "Bench Press (Barbell)"}'
```

```json
{
  "exercise_name": "Bench Press (Barbell)",
  "predicted_volume_kg": 1832.2,
  "estimated_weight_kg": 59.1,
  "estimated_sets": 4,
  "estimated_reps_per_set": 7.8,
  "last_session_date": "2026-04-29",
  "last_session_volume_kg": 1910.0,
  "features_used": { "..." : "...", },
  "model_version": "hevy-fti-model:latest"
}
```

- `estimated_weight_kg` = `predicted_volume_kg / last_session_total_reps` (null if unknown)
- `estimated_sets` / `estimated_reps_per_set` come from the last session

### `POST /predict/batch`

Predict for multiple exercises at once.

```bash
curl -X POST http://localhost:8080/predict/batch \
  -H "Content-Type: application/json" \
  -d '{"exercises": ["Bench Press (Barbell)", "Pull Up"]}'
```

```json
{
  "predictions": [
    { "exercise_name": "Bench Press (Barbell)", "predicted_volume_kg": 1832.2, "...": "..." },
    { "exercise_name": "Pull Up", "predicted_volume_kg": 0.0, "...": "..." }
  ]
}
```

Partial failures are tolerated — exercises with no history are skipped and the rest are returned.

## Required Environment Variables

| Variable            | Description                           |
|---------------------|---------------------------------------|
| `DAGSHUB_TOKEN`     | DagsHub personal access token         |
| `DAGSHUB_REPO_OWNER`| DagsHub username                      |
| `DAGSHUB_REPO_NAME` | Repository name on DagsHub            |
| `MLFLOW_MODEL_URI`  | (optional) Model URI, default: `models:/hevy-fti-model/latest` |
