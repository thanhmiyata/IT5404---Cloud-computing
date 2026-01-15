# Demo Runbook (15 minutes)

## Setup (pre-demo)
- Seed 1 exam with 30-50 questions into DB.
- Deploy exam-api + score-worker.
- Confirm UIs/health:
  - POST submit returns 202
  - GET result works

## Demo steps
1) Show architecture slide (1 min)
2) Show Monitoring dashboards baseline (1 min)
3) Run k6 spike scenario (2-3 min)
4) Observe:
   - exam-api stable 202 responses
   - Pub/Sub backlog rises then falls
   - score-worker scales out/in
5) Pick some submissionId -> show GET result scored (1 min)
6) Show graphs screenshots for report (1 min)
7) Wrap up: SLO/metrics summary (1 min)

## Cleanup
- Delete Cloud Run services (or keep)
- Destroy DB (optional)
