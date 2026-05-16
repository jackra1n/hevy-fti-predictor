#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="project-584fe454-7c29-44c0-b2d"
REGION="europe-west1"
REPO_NAME="hevy-fti-predictor"
IMAGE_NAME="hevy-inference"
TAG="latest"
SERVICE_NAME="hevy-fti-inference"

# load DAGSHUB_TOKEN from .env if available
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ -z "${DAGSHUB_TOKEN:-}" ]; then
  echo "ERROR: DAGSHUB_TOKEN is not set."
  echo "Please set it in your environment or in a .env file."
  exit 1
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}"

echo "=== Deploy Hevy FTI Inference to Cloud Run ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $IMAGE_URI"
echo ""

echo "[1/3] Building and pushing image via Cloud Build..."
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions="_IMAGE_URI=${IMAGE_URI}" \
  --project="$PROJECT_ID"
echo "Done."

echo ""
echo "[2/3] Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --platform managed \
  --set-env-vars "DAGSHUB_TOKEN=${DAGSHUB_TOKEN},DAGSHUB_REPO_OWNER=jackra1n,DAGSHUB_REPO_NAME=hevy-fti-predictor" \
  --allow-unauthenticated \
  --memory "1Gi" \
  --cpu "1" \
  --min-instances 1 \
  --max-instances 1 \
  --project="$PROJECT_ID"
echo "Done."

echo ""
echo "[3/3] Fetching service URL..."
URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)" --project="$PROJECT_ID")
echo ""
echo "=== Deployment complete ==="
echo ""
echo "Service URL: $URL"
echo ""
echo "Test it:"
echo "  curl ${URL}/health"
echo "  curl -X POST ${URL}/predict -H 'Content-Type: application/json' -d '{\"exercise_name\":\"Pull Up\"}'"
