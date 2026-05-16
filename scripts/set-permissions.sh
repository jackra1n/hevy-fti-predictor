#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="project-584fe454-7c29-44c0-b2d"

# default compute service account is used by cloud build
COMPUTE_SA="389703270212-compute@developer.gserviceaccount.com"

echo "=== Setting GCP permissions for Cloud Build / Cloud Run ==="
echo ""
echo "Granting necessary roles to $COMPUTE_SA..."
echo ""

# read source tarball from gcs
echo "[1/4] roles/storage.objectViewer"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/storage.objectViewer" \
  --condition=None >/dev/null 2>&1 || true

# push built images
echo "[2/4] roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/artifactregistry.writer" \
  --condition=None >/dev/null 2>&1 || true

# deploy services
echo "[3/4] roles/run.developer"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/run.developer" \
  --condition=None >/dev/null 2>&1 || true

# extra build permissions
echo "[4/4] roles/cloudbuild.builds.builder"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/cloudbuild.builds.builder" \
  --condition=None >/dev/null 2>&1 || true

echo ""
echo "=== Done ==="
