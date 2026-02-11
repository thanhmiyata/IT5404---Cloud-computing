# Deploy Runbook (gcloud) — Exam Scoring on GCP (Cloud Run + Pub/Sub Push + Cloud SQL)

## 0) Prereqs
- You have `gcloud` installed and can run commands in terminal.
- You have permissions to create: Artifact Registry, Cloud Run, Pub/Sub, Cloud SQL, Secret Manager.
- You already have 2 container images (or Dockerfiles) for:
  - `exam-api`
  - `score-worker`

> Recommended: use the same region for all resources.

---

## 1) Set variables (EDIT THESE)
```bash
export PROJECT_ID="<PROJECT_ID>"
export REGION="<REGION>"                 # e.g. asia-southeast1
export REPO="exam-repo"                  # Artifact Registry repo name

export DB_INSTANCE="examdb-pg"
export DB_NAME="examdb"
export DB_USER="examuser"

export TOPIC="score-jobs"
export SUBSCRIPTION="score-jobs-sub"

export EXAM_API_SERVICE="exam-api"
export WORKER_SERVICE="score-worker"
export WORKER_PUSH_PATH="/pubsub/push"   # worker HTTP endpoint for Pub/Sub push

# Choose strong passwords/keys
export DB_PASSWORD="<DB_PASSWORD>"
export API_KEY="<API_KEY>"               # optional demo auth
export JWT_SECRET="<JWT_SECRET>"         # optional demo auth
````

Set active project:

```bash
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"
```

Authenticate (ADC is useful for tooling; ok to run once):

```bash
gcloud auth login
gcloud auth application-default login
```

---

## 2) Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  pubsub.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com
```

---

## 3) Create Artifact Registry (Docker)

```bash
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Exam scoring images"
```

Configure Docker auth for Artifact Registry:

```bash
gcloud auth configure-docker "$REGION-docker.pkg.dev"
```

---

## 4) Create secrets in Secret Manager

Create secrets (only first time):

```bash
printf "%s" "$DB_PASSWORD" | gcloud secrets create db-password --data-file=-
printf "%s" "$API_KEY"      | gcloud secrets create api-key      --data-file=-
printf "%s" "$JWT_SECRET"   | gcloud secrets create jwt-secret   --data-file=-
```

If secret already exists, update instead:

```bash
printf "%s" "$DB_PASSWORD" | gcloud secrets versions add db-password --data-file=-
printf "%s" "$API_KEY"      | gcloud secrets versions add api-key      --data-file=-
printf "%s" "$JWT_SECRET"   | gcloud secrets versions add jwt-secret   --data-file=-
```

---

## 5) Create Cloud SQL (PostgreSQL)

### 5.1 Create instance (simple/public IP for fastest setup)

```bash
gcloud sql instances create "$DB_INSTANCE" \
  --database-version=POSTGRES_15 \
  --region="$REGION" \
  --cpu=2 \
  --memory=8GB \
  --storage-size=50GB \
  --storage-type=SSD \
  --enable-storage-auto-increase \
  --availability-type=zonal
```

### 5.2 Create database + user

```bash
gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE"

gcloud sql users create "$DB_USER" \
  --instance="$DB_INSTANCE" \
  --password="$DB_PASSWORD"
```

### 5.3 Get Cloud SQL connection name

```bash
export CLOUDSQL_CONN_NAME="$(gcloud sql instances describe "$DB_INSTANCE" --format='value(connectionName)')"
echo "CLOUDSQL_CONN_NAME=$CLOUDSQL_CONN_NAME"
```

> Note: We will connect Cloud Run to Cloud SQL via Cloud SQL connector using `--add-cloudsql-instances`.

---

## 6) Build & push container images

You can use either:

* A) local docker build + docker push
* B) Cloud Build (recommended for consistency)

### Option A — Local Docker build/push

Tag format:
`$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/<image>:<tag>`

```bash
export EXAM_API_IMG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/exam-api:latest"
export WORKER_IMG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/score-worker:latest"
```

Build & push (run from your repo root or proper service directories):

```bash
# exam-api
docker build -t "$EXAM_API_IMG" ./services/exam-api
docker push "$EXAM_API_IMG"

# score-worker
docker build -t "$WORKER_IMG" ./services/score-worker
docker push "$WORKER_IMG"
```

### Option B — Cloud Build (if you prefer)

```bash
export EXAM_API_IMG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/exam-api:latest"
export WORKER_IMG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/score-worker:latest"

gcloud builds submit ./services/exam-api --tag "$EXAM_API_IMG"
gcloud builds submit ./services/score-worker --tag "$WORKER_IMG"
```

---

## 7) Create Pub/Sub topic

```bash
gcloud pubsub topics create "$TOPIC"
```

(Optional) Create a dead-letter topic later (phase 2).

---

## 8) Deploy Cloud Run: exam-api (public)

### 8.1 Deploy

```bash
gcloud run deploy "$EXAM_API_SERVICE" \
  --image="$EXAM_API_IMG" \
  --region="$REGION" \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=512Mi \
  --concurrency=80 \
  --max-instances=200 \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,PUBSUB_TOPIC=$TOPIC,APP_ENV=prod" \
  --set-secrets="DB_PASSWORD=db-password:latest,API_KEY=api-key:latest,JWT_SECRET=jwt-secret:latest" \
  --add-cloudsql-instances="$CLOUDSQL_CONN_NAME" \
  --set-env-vars="DB_HOST=/cloudsql/$CLOUDSQL_CONN_NAME,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER"
```

### 8.2 Get exam-api URL

```bash
export EXAM_API_URL="$(gcloud run services describe "$EXAM_API_SERVICE" --region="$REGION" --format='value(status.url)')"
echo "EXAM_API_URL=$EXAM_API_URL"
```

Quick health check:

```bash
curl -sS "$EXAM_API_URL/healthz" || true
```

---

## 9) Deploy Cloud Run: score-worker (Pub/Sub push target)

### 9.1 Deploy worker

For fastest demo, allow unauthenticated (phase 2 can switch to OIDC auth).

```bash
gcloud run deploy "$WORKER_SERVICE" \
  --image="$WORKER_IMG" \
  --region="$REGION" \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=512Mi \
  --concurrency=5 \
  --max-instances=300 \
  --timeout=300 \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,APP_ENV=prod" \
  --set-secrets="DB_PASSWORD=db-password:latest" \
  --add-cloudsql-instances="$CLOUDSQL_CONN_NAME" \
  --set-env-vars="DB_HOST=/cloudsql/$CLOUDSQL_CONN_NAME,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER"
```

### 9.2 Get worker URL

```bash
export WORKER_URL="$(gcloud run services describe "$WORKER_SERVICE" --region="$REGION" --format='value(status.url)')"
echo "WORKER_URL=$WORKER_URL"
echo "WORKER_PUSH_ENDPOINT=$WORKER_URL$WORKER_PUSH_PATH"
```

---

## 10) Create Pub/Sub push subscription -> worker endpoint

```bash
gcloud pubsub subscriptions create "$SUBSCRIPTION" \
  --topic="$TOPIC" \
  --push-endpoint="$WORKER_URL$WORKER_PUSH_PATH" \
  --ack-deadline=30 \
  --min-retry-delay=10s \
  --max-retry-delay=600s
```

> Note:
>
> * Pub/Sub push acks on HTTP 2xx from worker.
> * Non-2xx triggers retry.
> * Worker must be idempotent by submissionId.

---

## 11) IAM notes (important)

### 11.1 Cloud Run access

Because we used `--allow-unauthenticated` for worker, Pub/Sub can invoke it without IAM binding.
Phase 2 hardening:

* Use Pub/Sub push with OIDC token and require authenticated invocations on worker.

### 11.2 Cloud SQL access

Cloud Run service accounts need Cloud SQL Client role.
If deploy fails to connect DB, grant role:

```bash
export RUN_SA="$(gcloud run services describe "$EXAM_API_SERVICE" --region="$REGION" --format='value(spec.template.spec.serviceAccountName)')"
echo "EXAM_API serviceAccount=$RUN_SA"
```

If empty, it uses default compute SA:
`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`

Grant Cloud SQL Client to the correct SA:

```bash
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
export DEFAULT_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEFAULT_SA" \
  --role="roles/cloudsql.client"
```

---

## 12) Initialize database schema

### Option A (quick) — Use Cloud SQL proxy locally

1. Install cloud-sql-proxy (if needed)
2. Run proxy:

```bash
cloud-sql-proxy "$CLOUDSQL_CONN_NAME" --port 5432
```

3. Apply schema (from repo):

```bash
psql "host=127.0.0.1 port=5432 dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD sslmode=disable" -f ./db/schema.sql
```

### Option B — Use Cloud SQL Studio / Console SQL

* Open Cloud SQL -> Query editor -> paste schema.sql

---

## 13) Seed 1 demo exam (minimum for testing)

You have 2 options:

* If you implement admin endpoint: POST /admin/exams
* Or insert directly into DB (SQL seed)

(Example curl if admin endpoint exists)

```bash
curl -sS -X POST "$EXAM_API_URL/v1/admin/exams" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d @./seed/exam_001.json
```

---

## 14) Smoke test end-to-end (manual)

### 14.1 Submit

```bash
curl -sS -X POST "$EXAM_API_URL/v1/exams/exam_001/submissions" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "userId":"u_123",
    "answers":[
      {"questionId":"q1","choice":"B"},
      {"questionId":"q2","choice":"A"}
    ],
    "clientSubmittedAt":"2026-01-15T10:00:00Z"
  }'
```

Expect: `202` with `submissionId`.

### 14.2 Poll result

```bash
export SUB_ID="<submissionId_from_previous_response>"

curl -sS "$EXAM_API_URL/v1/submissions/$SUB_ID" \
  -H "x-api-key: $API_KEY"
```

Expect: status moves from RECEIVED/SCORING -> SCORED with score.

---

## 15) Observability (what to watch during load test)

* Cloud Run `exam-api`:

  * Request count, p95 latency, 5xx
  * Instance count scale out/in
* Pub/Sub subscription:

  * backlog, oldest unacked message age
* Cloud Run `score-worker`:

  * instance count, CPU/memory
* Cloud SQL:

  * CPU, connections

---

## 16) Cleanup (avoid costs)

### Delete Cloud Run services

```bash
gcloud run services delete "$EXAM_API_SERVICE" --region="$REGION" --quiet
gcloud run services delete "$WORKER_SERVICE" --region="$REGION" --quiet
```

### Delete Pub/Sub resources

```bash
gcloud pubsub subscriptions delete "$SUBSCRIPTION"
gcloud pubsub topics delete "$TOPIC"
```

### Delete Cloud SQL instance

```bash
gcloud sql instances delete "$DB_INSTANCE" --quiet
```

### Delete secrets (optional)

```bash
gcloud secrets delete db-password --quiet
gcloud secrets delete api-key --quiet
gcloud secrets delete jwt-secret --quiet
```

### Delete Artifact Registry repo (optional)

```bash
gcloud artifacts repositories delete "$REPO" --location="$REGION" --quiet
```

---

## 17) Troubleshooting quick notes

* Pub/Sub push not delivering:

  * Check worker endpoint path matches `WORKER_PUSH_PATH`
  * Check worker returns 2xx quickly (or within timeout)
  * Check Cloud Run logs for incoming requests
* DB connection errors:

  * Ensure `--add-cloudsql-instances` set
  * Ensure correct env: `DB_HOST=/cloudsql/<conn_name>`
  * Ensure Cloud SQL Client role on service account
* High 5xx under load:

  * Reduce worker concurrency
  * Increase Cloud SQL tier or add pooling
  * Ensure submit endpoint returns 202 and does not do heavy work
