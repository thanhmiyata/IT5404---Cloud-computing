# Observability (Monitoring & Logging)

## Must-have dashboards
1) Cloud Run (exam-api)
- request count
- p95 latency
- 4xx/5xx
- instance count

2) Cloud Run (score-worker)
- request count
- instance count
- CPU/memory
- (custom) jobs processed / sec (from logs)

3) Pub/Sub
- subscription backlog
- oldest unacked message age

4) Cloud SQL
- CPU utilization
- active connections
- disk / iops (optional)

## Logging fields (recommend)
- traceId
- submissionId
- status transitions
- scoring duration ms
- db duration ms
