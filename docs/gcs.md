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
