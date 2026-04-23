# Hevy API Documentation

> Base URL: `https://api.hevyapp.com`

## Authentication

All requests must include your API key in the `api-key` header:

```http
GET /v1/workouts HTTP/1.1
Host: api.hevyapp.com
api-key: <YOUR_API_KEY>
```

The API key is stored in the `.env` file as `HEVY_API_KEY` and loaded at runtime.

## Endpoints

### 1. List Workouts

```http
GET /v1/workouts?page={page}&pageSize={pageSize}
```

Returns a paginated list of workouts.

**Query Parameters:**

| Parameter  | Type | Default | Description                        |
|------------|------|---------|------------------------------------|
| `page`     | int  | 1       | Page number (1-indexed)            |
| `pageSize` | int  | 10      | Items per page (maximum 10)        |

**Response Structure:**

```json
{
  "workouts": [
    {
      "id": "f1085cdb-32b2-4003-967d-53a3af8eaecb",
      "title": "Push Day",
      "description": "",
      "start_time": "2024-01-01T10:00:00Z",
      "end_time": "2024-01-01T11:00:00Z",
      "updated_at": "2024-01-01T11:00:00Z",
      "created_at": "2024-01-01T11:00:00Z",
      "exercises": [
        {
          "index": 0,
          "title": "Bench Press",
          "notes": "",
          "exercise_template_id": "abc123",
          "superset_id": null,
          "sets": [
            {
              "index": 0,
              "type": "normal",
              "weight_kg": 80.0,
              "reps": 10,
              "distance_meters": null,
              "duration_seconds": null,
              "rpe": null
            }
          ]
        }
      ]
    }
  ],
  "page": 1,
  "page_count": 5
}
```

### 2. Get Single Workout

```http
GET /v1/workouts/{workout_id}
```

Returns full details for a specific workout.

**Path Parameters:**

| Parameter   | Type   | Description              |
|-------------|--------|--------------------------|
| `workout_id`| string | UUID of the workout      |

## Webhooks

Hevy supports webhooks for real-time notifications when a new workout is created.

**Webhook Payload:**

```json
{
  "workoutId": "f1085cdb-32b2-4003-967d-53a3af8eaecb"
}
```

- **Method:** `POST`
- **Expected Response:** `200 OK` within 5 seconds
- **Authorization Header:** You can configure a custom auth header that Hevy will send with each request.

> **Note:** Webhooks are optional for this project. The pipeline currently uses a 24-hour polling schedule via GitHub Actions rather than webhook-driven ingestion.

## Data Model

### Workout

| Field       | Type     | Description                          |
|-------------|----------|--------------------------------------|
| `id`        | string   | UUID                                 |
| `title`     | string   | User-defined workout name            |
| `start_time`| ISO 8601 | When the workout began               |
| `end_time`  | ISO 8601 | When the workout ended               |
| `exercises` | array    | List of exercises performed          |

### Exercise

| Field                  | Type   | Description                          |
|------------------------|--------|--------------------------------------|
| `title`                | string | Exercise name                        |
| `exercise_template_id` | string | Reference to global exercise template|
| `superset_id`          | string | Superset grouping identifier         |
| `sets`                 | array  | List of performed sets               |

### Set

| Field              | Type    | Description                          |
|--------------------|---------|--------------------------------------|
| `type`             | string  | `normal`, `warmup`, `failure`, etc.  |
| `weight_kg`        | float   | Weight in kilograms                  |
| `reps`             | integer | Repetitions performed                |
| `distance_meters`  | float   | For cardio exercises                 |
| `duration_seconds` | integer | For timed exercises                  |
| `rpe`              | float   | Rate of Perceived Exertion (1-10)    |

## Rate Limits

Refer to the official Hevy API documentation for current rate limits. The client implements basic pagination to stay within limits when fetching historical data.
