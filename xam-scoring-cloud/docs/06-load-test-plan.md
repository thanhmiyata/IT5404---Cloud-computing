# Load Test Plan (k6)

## Test objectives
- Prove elastic scaling under spike traffic.
- Collect metrics for report: p95/p99 latency, error rate, throughput, backlog, scale events.

## Workloads
A) Baseline: 50 RPS, 5 minutes
B) Ramp-up: 50 -> 200 -> 500 -> 1000 RPS (2 min each)
C) Spike (end-of-exam): 100 RPS (2 min) -> 5000 RPS (60s) -> 100 RPS (2 min)
D) Fluctuating: 15 minutes sinus-like

## Validation
- Random answers payload size realistic (e.g. 20-50 questions).
- Measure:
  - HTTP p95 for POST /submit
  - 5xx rate
  - time to score (poll GET /submissions/{id} sampled)

## Output artifacts
- k6 summary output
- CSV/JSON metrics export
- Screenshot Cloud Run instance scaling + Pub/Sub backlog graphs
