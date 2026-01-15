# Scaling & SLO

## SLO (demo-level)
- Submit endpoint (exam-api):
  - p95 latency < 300ms under baseline, < 800ms under spike (202 response)
  - error rate (5xx) < 1%
- End-to-end scoring (submit -> SCORED):
  - p95 completion time < 30s for spike scenario (tunable)

## Cloud Run knobs (suggested)
exam-api:
- concurrency: 80
- max instances: 200
- cpu: 1
- memory: 512Mi/1Gi

score-worker:
- concurrency: 5 (CPU bound thì giảm)
- max instances: 300
- cpu: 1-2
- memory: 512Mi/1Gi

## Bottleneck assumptions
- Cloud SQL connections can be choke point.
- Use pooling & limit worker concurrency if DB saturates.
