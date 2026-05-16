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

### Workload Identity Federation Setup

In the Google Cloud Console, go to **IAM & Admin → Workload Identity Federation**.

#### 1. Create a Pool

- Click **Create Pool**
- **Name**: `GitHub Actions CI` (or anything descriptive)
- **Pool ID**: `github-actions-pool` (used later in IAM policies)
- Leave other fields as default, click **Continue**

#### 2. Add a Provider

On the pool page, click **Add Provider**:

- **Provider name**: `Github OIDC`
- **Issuer (URL)**: `https://token.actions.githubusercontent.com`
- **Attribute conditions**: `assertion.repository_owner=='<your-github-username>'`

  This is *required*. It restricts which GitHub accounts can use this provider. Use your GitHub username (personal account) or organization name.

- **Attribute mapping** — add these four mappings via the "Add" button:

  | Google label / key | Claim / value |
  |---|---|
  | `google.subject` | `assertion.sub` |
  | `attribute.actor` | `assertion.actor` |
  | `attribute.repository` | `assertion.repository` |
  | `attribute.repository_owner` | `assertion.repository_owner` |

  Note: no spaces around `=` — the UI uses separate input columns.

- Click **Save**

#### 3. Create a Service Account

Go to **IAM & Admin → Service Accounts → Create Service Account**:

- **Name**: `github-actions` (or similar)
- **Role**: **Storage Object Admin**
- Click **Done** — do **not** create a key

#### 4. Grant the Pool Access to the Service Account

Go back to **Workload Identity Federation**, open your pool:

- Click **Grant Access**
- Select **Grant access using service account impersonation**
- Select your service account (`github-actions@<PROJECT>.iam.gserviceaccount.com`)
- In **Select principals**, use the dropdown to select `repository` and type your full repo path in the text field:
  - Dropdown: `repository`
  - Text field: `<your-username>/<repo-name>`

  This builds the binding: `attribute.repository==<your-username>/<repo-name>`

- Click **Save**

### gcloud installation

gcloud is managed through mise:

```toml
[tools]
gcloud = "latest"
```

## Cloud Run

The inference API is deployed to Cloud Run. The following APIs must be enabled:

- `run.googleapis.com`
- `artifactregistry.googleapis.com`
- `cloudbuild.googleapis.com`

Run `./scripts/setup-gcp.sh` to enable them automatically.

The deploy script (`./scripts/deploy.sh`) uses Google Cloud Build to build the inference image (via `cloudbuild.yaml`) and pushes it to Artifact Registry before deploying to Cloud Run.

### CI/CD Deployment

The `.github/workflows/deploy.yml` workflow automatically deploys the inference service after every successful training run. It builds the Docker image directly on the GitHub Actions runner and pushes it to Artifact Registry — no Cloud Build required. The WIF service account needs these additional IAM roles beyond the Storage Object Admin role already granted:

| Role | Scope | Purpose |
|------|-------|---------|
| `roles/storage.objectAdmin` | Project | DVC push/pull to GCS |
| `roles/artifactregistry.writer` | Project | Push Docker images |
| `roles/run.admin` | Project | Deploy to Cloud Run |
| `roles/iam.serviceAccountUser` | Compute SA | Let Cloud Run use the Compute SA |

Grant the project-level roles:

```bash
WIF_SA="github-actions@<PROJECT>.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:${WIF_SA}" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:${WIF_SA}" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:${WIF_SA}" \
  --role="roles/run.admin"
```

Grant the Compute SA binding:

```bash
COMPUTE_SA="389703270212-compute@developer.gserviceaccount.com"

gcloud iam service-accounts add-iam-policy-binding "${COMPUTE_SA}" \
  --member="serviceAccount:${WIF_SA}" \
  --role="roles/iam.serviceAccountUser"
```

See [inference.md](inference.md) for the full inference deployment guide.
