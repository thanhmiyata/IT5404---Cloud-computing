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
PUBLIC_IP="34.143.226.181"
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

## Troubleshooting
- If the endpoint returns `Connection refused`: Check Docker containers (`docker-compose ps`) and Firewall rules.
- If Dashboard shows "Connection Error": Ensure `config.js` has the correct IP and Mixed Content (HTTP/HTTPS) is not blocking requests if using SSL (currently HTTP only).
