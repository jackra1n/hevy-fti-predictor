# Google Cloud Storage

DVC remote storage is backed by a Google Cloud Storage bucket.

## Setup

### Create a bucket

Create a bucket in the Google Cloud Console with default settings. Standard storage class, uniform access control — nothing special needed.

### Authenticate

Authentication uses Application Default Credentials via the gcloud CLI:

```bash
gcloud auth login                         # sign in with your Google account
gcloud config set project <PROJECT_ID>    # set the GCP project
gcloud auth application-default login     # create ADC credentials
```

Credentials are written to `~/.config/gcloud/application_default_credentials.json`. DVC picks them up automatically — no service account key file needed.

### Configure DVC remote

```bash
dvc remote add -d gcs gs://<your-bucket>/<path>
```

The `-d` flag sets it as the default remote. DVC writes non-sensitive config to `.dvc/config` (committed to Git).

## CI/CD (GitHub Actions)

For automated pipelines, use **Workload Identity Federation** to let GitHub Actions authenticate without long-lived keys. The OIDC token from the GitHub Actions run is exchanged for a short-lived GCP access token.

Requirements:
- A Workload Identity Pool and Provider in GCP (issuer: `https://token.actions.githubusercontent.com`)
- A service account with **Storage Object Admin** and **Workload Identity User** roles — created without a key
- `google-github-actions/auth@v2` in the workflow YAML

### gcloud installation

gcloud is managed through mise:

```toml
[tools]
gcloud = "latest"
```
