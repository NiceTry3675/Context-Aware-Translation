# GCP Backend Deployment Guide

This guide covers moving the backend from Railway to GCP while keeping the
frontend on Vercel.

## Target Architecture

- Cloud Run service: FastAPI API server.
- Cloud Run worker pool: Celery worker for translation, validation, post-editing, illustrations, events, and maintenance queues.
- Cloud Run worker pool: Celery beat, fixed to one instance.
- Cloud Run job: Alembic migration runner.
- Cloud SQL for PostgreSQL: production database.
- Memorystore for Redis: Celery broker and result backend.
- Cloud Storage bucket mounted at `/mnt/trans-storage`: uploads, job logs, outputs, and legacy translated files.
- Secret Manager: runtime secrets injected into Cloud Run.

The frontend stays on Vercel. After backend cutover, update `NEXT_PUBLIC_API_URL`
to the Cloud Run API URL.

## Required GCP Resources

Use one region for Cloud Run, Cloud SQL, Memorystore, and the VPC connector.
For Korea-first latency, use `asia-northeast3`.

Required APIs:

```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com \
  storage.googleapis.com
```

Create or verify these resources:

- Artifact Registry Docker repository for the backend image.
- Cloud SQL PostgreSQL instance and database, for example `trans_prod`.
- Memorystore Redis instance reachable from Cloud Run through a VPC connector.
- Cloud Storage bucket for runtime files.
- Runtime service account with:
  - `roles/cloudsql.client`
  - `roles/secretmanager.secretAccessor`
  - `roles/storage.objectUser` on the runtime bucket
  - Artifact Registry read access if the image repository is in another project.

## Secret Manager

Create these secrets before running the GitHub workflow:

```bash
printf '%s' "$DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=-
printf '%s' "$REDIS_URL" | gcloud secrets create REDIS_URL --data-file=-
printf '%s' "$CLERK_SECRET_KEY" | gcloud secrets create CLERK_SECRET_KEY --data-file=-
printf '%s' "$CLERK_WEBHOOK_SECRET" | gcloud secrets create CLERK_WEBHOOK_SECRET --data-file=-
printf '%s' "$ADMIN_SECRET_KEY" | gcloud secrets create ADMIN_SECRET_KEY --data-file=-
printf '%s' "$SECRET_KEY" | gcloud secrets create SECRET_KEY --data-file=-
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
```

`OPENROUTER_API_KEY` is optional. If a secret with that name exists, the deploy
workflow injects it automatically.

For Cloud SQL over the Cloud Run socket, use this `DATABASE_URL` shape:

```text
postgresql+psycopg2://trans_app:<password>@/trans_prod?host=/cloudsql/<project>:<region>:<instance>
```

For Memorystore, use:

```text
redis://<memorystore-private-ip>:6379/0
```

## GitHub Actions Variables

Set these repository variables:

```text
GOOGLE_CLOUD_PROJECT=<project-id>
GOOGLE_CLOUD_LOCATION=asia-northeast3
ARTIFACT_REGISTRY_REPOSITORY=<artifact-registry-repo>
SERVICE_ACCOUNT_EMAIL=<deploy-service-account>
GCP_WIF_PROVIDER=<workload-identity-provider>
CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT=<runtime-service-account>
CLOUD_RUN_BACKEND_SERVICE=<api-service-name>
CLOUD_RUN_WORKER_SERVICE=<worker-pool-name>
CLOUD_RUN_BEAT_SERVICE=<beat-pool-name>
CLOUD_RUN_MIGRATION_JOB=<migration-job-name>
CLOUD_SQL_INSTANCE=<project>:<region>:<instance>
CLOUD_RUN_VPC_CONNECTOR=<connector-name>
GCS_BUCKET=<runtime-bucket-name>
GCS_PREFIX=prod
CORS_ORIGINS=https://<vercel-app-domain>
```

Optional scaling variables:

```text
CLOUD_RUN_API_MIN_INSTANCES=1
CLOUD_RUN_WORKER_INSTANCES=1
CLOUD_RUN_BEAT_INSTANCES=1
```

The workflow builds the Docker image, runs the migration job, deploys the API
service, and deploys the worker and beat worker pools.

## Railway DB Cutover

This migration intentionally moves only the Railway PostgreSQL data. Existing
Railway file outputs, job logs, and uploaded images are not copied. Old jobs may
therefore keep their metadata but fail to download file artifacts. New jobs store
files in the mounted Cloud Storage bucket.

During cutover:

```bash
pg_dump --format=custom --no-owner --no-acl "$RAILWAY_DATABASE_URL" > railway-prod.dump
pg_restore --clean --if-exists --no-owner --no-acl --dbname="$CLOUD_SQL_DATABASE_URL" railway-prod.dump
```

After restore, run the GitHub workflow manually once from `workflow_dispatch`.

## External Service Cutover

- Vercel: set `NEXT_PUBLIC_API_URL` to the Cloud Run API URL and redeploy.
- Backend CORS: set `CORS_ORIGINS` to the Vercel production domain.
- Clerk: update webhook endpoint to `https://<cloud-run-api-url>/api/v1/webhooks/clerk`.

## Smoke Tests

After deployment:

```bash
curl "https://<cloud-run-api-url>/"
curl "https://<cloud-run-api-url>/api/v1/community/categories"
```

Then test from the Vercel UI:

- Sign in.
- Upload a small text file and start translation.
- Confirm Celery progress updates.
- Download translated output.
- Upload a community image and verify `/static/community/...` loads.
