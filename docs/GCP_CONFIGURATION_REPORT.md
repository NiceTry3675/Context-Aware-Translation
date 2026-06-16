# GCP Production Configuration Report

Generated: 2026-06-16

This report describes the production GCP configuration for the
Context-Aware Translation backend after the Cloud Run Jobs background
processing migration.

## Project

- Project ID: `trans-prod-260616-3fa1`
- Project name: `Context Translation Prod`
- Project number: `670808329530`
- Primary region: `asia-northeast3`
- Lifecycle state: `ACTIVE`

## Runtime Topology

- Frontend remains on Vercel: `https://catrans.me`
- Backend API runs on Cloud Run service `trans-api`
- Background processing runs on Cloud Run job `trans-background-job`
- Alembic migrations run through Cloud Run job `trans-migrate`
- Maintenance runs through Cloud Scheduler job `trans-maintenance`
- PostgreSQL runs on Cloud SQL instance `trans-prod-db`
- Runtime files are stored in Cloud Storage bucket `trans-prod-260616-3fa1-runtime`
- Container images are stored in Artifact Registry repository `trans-backend`

## Cloud Run

### API Service

- Service: `trans-api`
- URL: `https://trans-api-inn34takza-du.a.run.app`
- Latest ready revision: `trans-api-00007-ljm`
- Traffic: `100%` to latest revision
- Image: `asia-northeast3-docker.pkg.dev/trans-prod-260616-3fa1/trans-backend/trans-backend:8685cfbe3877b13ef4a62b8f0d517ac984747b9b`
- Runtime service account: `trans-runtime@trans-prod-260616-3fa1.iam.gserviceaccount.com`
- Execution environment: Gen 2
- Scaling: min `0`, max `3`
- Resources: CPU `1`, memory `1Gi`
- Cloud SQL connection: `trans-prod-260616-3fa1:asia-northeast3:trans-prod-db`
- Cloud Storage mount: bucket `trans-prod-260616-3fa1-runtime` mounted at `/mnt/trans-storage`
- Background executor: `cloud_run`
- Background job: `trans-background-job`

### Background Job

- Job: `trans-background-job`
- Runtime role: `job`
- Runtime service account: `trans-runtime@trans-prod-260616-3fa1.iam.gserviceaccount.com`
- Resources: CPU `2`, memory `2Gi`
- Tasks: `1`
- Parallelism: `1`
- Max retries: `0`
- Task timeout: `86400s` (24 hours)
- Cloud SQL connection: `trans-prod-260616-3fa1:asia-northeast3:trans-prod-db`
- Cloud Storage mount: bucket `trans-prod-260616-3fa1-runtime` mounted at `/mnt/trans-storage`

The API starts this job through Cloud Run Jobs `run` with environment variable
overrides. User-supplied AI keys are passed in the per-execution override
payload and are redacted before being stored in `task_executions`.

### Maintenance Scheduler

- Scheduler job: `trans-maintenance`
- Schedule: every 5 minutes
- Target: Cloud Run Jobs `run` endpoint for `trans-background-job`
- Payload: `BACKGROUND_TASK_NAME=backend.background.maintenance.run_maintenance`
- Runs outbox processing, temp cleanup, and stalled job watchdog

### Migration Job

- Job: `trans-migrate`
- Latest execution: `trans-migrate-mx4fh`
- Image: `asia-northeast3-docker.pkg.dev/trans-prod-260616-3fa1/trans-backend/trans-backend:8685cfbe3877b13ef4a62b8f0d517ac984747b9b`
- Runtime role: `migrate`
- Runs Alembic migrations with `RUN_MIGRATIONS=true`

## Runtime Environment

Shared production environment values:

- `APP_ENV=production`
- `ENVIRONMENT=production`
- `STORAGE_BACKEND=local`
- `UPLOAD_DIR=/mnt/trans-storage/prod/uploads`
- `JOB_STORAGE_BASE=/mnt/trans-storage/prod/logs/jobs`
- `LEGACY_TRANSLATED_DIR=/mnt/trans-storage/prod/translated_novel`
- `CORS_ORIGINS=https://catrans.me,https://context-aware-translation.vercel.app,https://www.catrans.me`

Role-specific values:

- API: `APP_RUNTIME_ROLE=api`, `RUN_MIGRATIONS=false`
- Background job: `APP_RUNTIME_ROLE=job`, `RUN_MIGRATIONS=false`
- Migration job: `APP_RUNTIME_ROLE=migrate`, `RUN_MIGRATIONS=true`
- API background execution: `BACKGROUND_EXECUTOR=cloud_run`
- Job timeout: `CLOUD_RUN_JOB_TIMEOUT=86400s`

## Cloud SQL

- Instance: `trans-prod-db`
- Connection name: `trans-prod-260616-3fa1:asia-northeast3:trans-prod-db`
- Version: PostgreSQL 16
- State: `RUNNABLE`
- Tier: `db-f1-micro`
- Availability: `ZONAL`
- Disk: `10GB`, `PD_SSD`
- Database: `trans_prod`
- Application user: `trans_app`
- Public IPv4: enabled
- Authorized networks: none
- Automated backups: disabled intentionally

## Network

- Cloud Run connects to Cloud SQL through the Cloud SQL connector.
- Redis, Memorystore, and Serverless VPC connector are no longer required for
  application runtime after the Cloud Run Jobs migration is deployed.

## Storage

- Bucket: `trans-prod-260616-3fa1-runtime`
- Location: `ASIA-NORTHEAST3`
- Storage class: `STANDARD`
- Uniform bucket-level access: enabled
- Versioning: not enabled
- Runtime prefix: `/prod`

## Artifact Registry

- Repository: `trans-backend`
- Location: `asia-northeast3`
- Format: Docker
- Mode: standard repository
- Latest deployed image tag: `8685cfbe3877b13ef4a62b8f0d517ac984747b9b`

## Secret Manager

Current runtime secrets:

- `DATABASE_URL`
- `CLERK_SECRET_KEY`
- `CLERK_WEBHOOK_SECRET`
- `ADMIN_SECRET_KEY`
- `SECRET_KEY`

Not present:

- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY`

`GEMINI_API_KEY` is intentionally not stored in GCP Secret Manager or injected
into Cloud Run. Gemini credentials are expected to be provided per request or
through another configured provider path.

## IAM And Deployment Automation

Runtime service account:

- `trans-runtime@trans-prod-260616-3fa1.iam.gserviceaccount.com`

Runtime service account project roles:

- `roles/artifactregistry.reader`
- `roles/cloudsql.client`
- `roles/run.developer` on `trans-background-job`
- `roles/run.jobsExecutorWithOverrides` on `trans-background-job`
- `roles/secretmanager.secretAccessor`

GitHub Actions deploy service account:

- `trans-github-deploy@trans-prod-260616-3fa1.iam.gserviceaccount.com`

Deploy service account project roles:

- `roles/artifactregistry.writer`
- `roles/cloudscheduler.admin`
- `roles/run.admin`
- `roles/secretmanager.secretAccessor`

Workload Identity Federation:

- Pool: `github-actions`
- Provider: `github`
- Provider resource: `projects/670808329530/locations/global/workloadIdentityPools/github-actions/providers/github`
- Issuer: `https://token.actions.githubusercontent.com`
- Repository condition: `assertion.repository=='NiceTry3675/Context-Aware-Translation'`

GitHub Actions:

- Workflow: `.github/workflows/deploy-gcp.yml`
- Trigger: push to `main`, or manual `workflow_dispatch`
- Last verified deployment commit: `8685cfbe3877b13ef4a62b8f0d517ac984747b9b`

## External Cutover

- Vercel production domain: `https://catrans.me`
- Vercel `NEXT_PUBLIC_API_URL`: Cloud Run API URL
- Clerk/Svix webhook endpoint: `https://trans-api-inn34takza-du.a.run.app/api/v1/webhooks/clerk`

## Verification

Latest verification after removing `GEMINI_API_KEY` from runtime secrets:

- Cloud Run API root returns `environment=production`
- `GET /api/v1/community/categories` returns HTTP `200`
- `catrans.me` returns HTTP `200`
- `GEMINI_API_KEY` no longer appears in Cloud Run API or migration job env
- `GEMINI_API_KEY` no longer exists in GCP Secret Manager

## Notes

- Cloud SQL automated backups are intentionally disabled.
- Cloud SQL public IPv4 is enabled, but no authorized networks are configured.
- After the Cloud Run Jobs workflow has deployed successfully and a background
  task has been verified, the old `trans-worker`, `trans-beat`,
  `trans-prod-redis`, and `trans-prod-connector` resources can be removed.
