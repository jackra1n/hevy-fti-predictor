#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="project-584fe454-7c29-44c0-b2d"
REGION="europe-west1"
REPO_NAME="hevy-fti-predictor"

echo "=== GCP Setup for Hevy FTI Inference ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

echo "[1/4] Enabling required APIs..."
gcloud services enable run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$PROJECT_ID"
echo "Done."

echo ""
echo "[2/4] Creating Artifact Registry repository (if not exists)..."
if gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Repository '$REPO_NAME' already exists."
else
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Docker images for hevy-fti-predictor" \
    --project="$PROJECT_ID"
  echo "Repository '$REPO_NAME' created."
fi

echo ""
echo "[3/4] Configuring Docker authentication for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
echo "Done."

echo ""
echo "[4/4] Verification..."
echo "Enabled APIs:"
gcloud services list --enabled --filter="config.name:(run.googleapis.com OR artifactregistry.googleapis.com OR cloudbuild.googleapis.com)" --format="table(config.name)" --project="$PROJECT_ID"

echo ""
echo "Artifact Registry repositories:"
gcloud artifacts repositories list --location="$REGION" --format="table(name,format,description)" --project="$PROJECT_ID"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Ensure billing is enabled for project $PROJECT_ID"
echo "     (Cloud Run requires a billing account)"
echo "  2. Run ./scripts/deploy.sh to build and deploy"
