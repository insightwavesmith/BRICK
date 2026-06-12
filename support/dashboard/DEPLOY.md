# Dashboard Deploy

This dashboard is a support projection. It reads a baked
`dashboard_export_packet` seed and optional `/ingest` pushes, then displays the
packet behind the operator's own access wall.

It is not source truth, success judgment, quality judgment, Movement authority,
a scheduler, a queue, a retry loop, a login system, or credential storage.

## Bake The Seed

Bake the static seed before building the dashboard image:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity \
  python3 support/operator/dashboard_export.py --bake-public
```

The command writes:

```text
support/dashboard/public/dashboard-data.json
```

Round-trip shape check:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import json
from pathlib import Path

path = Path("support/dashboard/public/dashboard-data.json")
packet = json.loads(path.read_text(encoding="utf-8"))
assert packet["source_truth"] is False
assert isinstance(packet["buildings"], list)
print({"source_truth": packet["source_truth"], "buildings": len(packet["buildings"])})
PY
```

The baked file is a projection seed only. The source of truth stays in the repo ledger and written Building evidence. Re-bake any time after the ledger changes.

## Cloud Run Plus IAP

Use the deployer's own values. Do not commit the ingest value.

```sh
export GCP_PROJECT_ID="<gcp-project-id>"
export GCP_PROJECT_NUMBER="$(gcloud projects describe "${GCP_PROJECT_ID}" --format='value(projectNumber)')"
export REGION="<region>"
export SERVICE_NAME="<cloud-run-service-name>"
export AR_REPO="<artifact-registry-repo>"
export IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}:$(date -u +%Y%m%dT%H%M%SZ)"
export INGEST_SECRET_VALUE="<operator-generated-ingest-value>"
```

Create the image repository if needed:

```sh
gcloud artifacts repositories create "${AR_REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${GCP_PROJECT_ID}"
```

Build and deploy the container:

```sh
gcloud builds submit support/dashboard \
  --tag="${IMAGE}" \
  --project="${GCP_PROJECT_ID}"

gcloud run deploy "${SERVICE_NAME}" \
  --project="${GCP_PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --no-allow-unauthenticated \
  --iap \
  --min-instances=0 \
  --set-env-vars=NODE_ENV=production,INGEST_SECRET="${INGEST_SECRET_VALUE}"
```

Grant Cloud Run Invoker to the IAP service agent:

```sh
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --project="${GCP_PROJECT_ID}" \
  --region="${REGION}" \
  --member="serviceAccount:service-${GCP_PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
  --role=roles/run.invoker
```

Then grant viewer access in IAP to the company's users or groups through their
own IAM policy. If this is the first IAP setup in a project without an
organization, Google Cloud may require the initial OAuth/IAP setup through the
Cloud Console before the CLI-only path is sufficient.

Scale-to-zero note: `--min-instances=0` means Cloud Run can keep no warm
instances when idle. That does not lose source truth because the dashboard is a
projection; cold start reloads the baked seed, and operators can re-bake from
the repo ledger at any time.

## Rotate INGEST_SECRET

Rotation is an environment update plus publisher update. The app stores no
credential body.

```sh
export NEW_INGEST_SECRET_VALUE="<new-operator-generated-ingest-value>"

gcloud run services update "${SERVICE_NAME}" \
  --project="${GCP_PROJECT_ID}" \
  --region="${REGION}" \
  --update-env-vars=INGEST_SECRET="${NEW_INGEST_SECRET_VALUE}"
```

Update the publisher that sends `POST /ingest` so it uses:

```text
x-ingest-secret: <new-operator-generated-ingest-value>
```

In `NODE_ENV=production`, `/ingest` refuses requests when `INGEST_SECRET` is
missing or still equal to the development fallback. Static viewing,
`/dashboard-data.json`, `/events`, and `/healthz` continue to serve.

## Generic Docker Behind An Authenticating Reverse Proxy

Bake first, then build and run the image with the operator's own container
runtime:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity \
  python3 support/operator/dashboard_export.py --bake-public

docker build -t "${SERVICE_NAME}:local" support/dashboard
docker run --rm \
  --name "${SERVICE_NAME}" \
  -e NODE_ENV=production \
  -e INGEST_SECRET="${INGEST_SECRET_VALUE}" \
  -p 127.0.0.1:8080:8080 \
  "${SERVICE_NAME}:local"
```

Put authentication in the reverse proxy. The dashboard app does not implement
accounts or sessions.

```nginx
upstream brick_dashboard_upstream {
  server 127.0.0.1:8080;
}

server {
  listen 443 ssl;
  server_name _;

  # Authentication belongs here: SSO, mTLS, VPN allowlist, or the company's
  # existing access gateway.

  location / {
    proxy_pass http://brick_dashboard_upstream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }

  location /events {
    proxy_pass http://brick_dashboard_upstream;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
  }
}
```

## Bare Node

Bare Node is for an operator-controlled host that already has an external
access wall. The app still has no account/session system.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity \
  python3 support/operator/dashboard_export.py --bake-public

cd support/dashboard
npm ci
npm run build
NODE_ENV=production INGEST_SECRET="${INGEST_SECRET_VALUE}" node server/index.mjs
```

For read-only static viewing without ingest, build the app after baking and
serve the generated `dist/` directory behind the company's access wall. Ingest
requires the Node server because `POST /ingest` and SSE live there.
