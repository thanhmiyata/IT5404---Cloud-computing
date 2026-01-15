# Architecture (GCP)

## Components
1) Cloud Run: exam-api (HTTP)
2) Pub/Sub: topic score-jobs + subscription (push/pull)
3) Cloud Run: score-worker (HTTP endpoint nhận push hoặc pull subscriber)
4) Cloud SQL: Postgres
5) (Optional) Memorystore Redis: cache exam/answer key
6) Secret Manager: DB creds, JWT secret/API keys
7) Cloud Monitoring + Logging

## Data Flow
Client -> exam-api
- Validate auth + basic validation payload
- Create submission record (RECEIVED)
- Publish message to Pub/Sub (score-jobs)
- Return 202 Accepted + submissionId

Pub/Sub -> score-worker
- Idempotency check (submission status)
- Load exam answer key (DB/Redis)
- Score calculation
- Update submission: SCORED + score + breakdown
- Persist answers (optional)
- Emit log/metrics

Client -> GET /submissions/{id}
- Poll until status SCORED
- Return score and summary

## Key Design Decisions
- Submit endpoint trả 202 để tránh timeout dưới spike.
- Queue decoupling: absorb bursts, allow worker autoscale.
- Idempotency: tránh chấm lại khi Pub/Sub retry / worker crash.
- Observability: đo latency submit, backlog queue, thời gian chấm.
