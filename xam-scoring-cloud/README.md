# Exam Scoring Cloud System

This repository contains a microservices-based exam scoring system designed to be deployed on a Cloud VM (GCP/AWS) using Docker Compose.

## Prerequisites

- **Docker** and **Docker Compose** installed on the VM.
- **Python 3** (available by default on most Linux distros) for serving the frontend.
- **GCP Firewall Rules** (or equivalent):
  - Allow Ingress TCP port `8080` (API).
  - Allow Ingress TCP port `8000` (Dashboard).

## Deployment Steps

### 1. Setup Environment
Ensure you are in the `xam-scoring-cloud` directory.
Create a `.env` file in the **project root** (parent directory of `xam-scoring-cloud`) to define your Public IP. 

```bash
# Example: /root/IT5404---Cloud-computing/.env
PUBLIC_IP="136.110.44.49"
```

> **Note**: The `generate_config.sh` script looks for `../.env` by default.

### 2. Start Backend Services
Use Docker Compose to build and start the API, Worker, and Database containers.

```bash
cd xam-scoring-cloud
docker-compose up -d --build
```

Check properly running services:
```bash
docker-compose ps
```

### 3. Configure Frontend
Run the configuration script to automatically inject your `PUBLIC_IP` into the dashboard settings.

```bash
chmod +x generate_config.sh
./generate_config.sh
```
*This triggers the creation of `config.js` with your production IP.*

### 4. Serve the Dashboard
Since the dashboard is a static HTML file, serve it using Python's built-in HTTP server:

```bash
# Run in background (recommended) or in a separate terminal
nohup python3 -m http.server 8000 &
```

## Access & Demo

- **Dashboard UI**: `http://<PUBLIC_IP>:8000/dashboard.html`
- **API Endpoint**: `http://<PUBLIC_IP>:8080`

### Test Submission (Demo)
You can trigger a submission from your local machine or the VM to see the dashboard scale/update in real-time.

```bash
curl -X POST http://<PUBLIC_IP>:8080/v1/exams/exam_001/submissions \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: change-me" \
  -d '{
    "userId": "demo_user_01",
    "answers": [
      {"questionId": "q1", "choice": "B"},
      {"questionId": "q2", "choice": "A"}
    ]
  }'
```

## Load Testing / Spike Demo

Simulate the "End-of-Exam" scenario where hundreds of students submit simultaneously.

### Option 1: Quick Demo with Live Monitoring

Uses `demo_spike.py` which shows baseline → burst → drain cycle with live stats.

```bash
# Default: 1000 submissions to localhost
python3 scripts/demo_spike.py

# Custom target and count
python3 scripts/demo_spike.py -n 2000 -c 100 --url http://<PUBLIC_IP>:8080/v1/exams/exam_001/submissions
```

### Option 2: Detailed Metrics Test

Uses `spike_load_test.py` for comprehensive metrics (p95/p99 latency, throughput, completion tracking).

```bash
# Basic spike test (1000 concurrent submissions)
python3 scripts/spike_load_test.py

# Test against remote VM
python3 scripts/spike_load_test.py --url http://<PUBLIC_IP>:8080 --count 1000

# Full test: wait until all submissions are SCORED
python3 scripts/spike_load_test.py --poll --poll-timeout 300

# Save results to JSON
python3 scripts/spike_load_test.py --poll --output results.json
```

**Metrics collected:**
- Success/failure rate
- Response time (avg, min, max, p95, p99)
- Throughput (submissions/sec)
- Time to complete all scoring (with `--poll`)

## Troubleshooting
- If the endpoint returns `Connection refused`: Check Docker containers (`docker-compose ps`) and Firewall rules.
- If Dashboard shows "Connection Error": Ensure `config.js` has the correct IP and Mixed Content (HTTP/HTTPS) is not blocking requests if using SSL (currently HTTP only).
