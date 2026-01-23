# PLAN — Online Exam Scoring (Elastic) on GCP (Cloud Run + Pub/Sub Push)

## 0) Mục tiêu
Xây dựng hệ thống chấm điểm thi trắc nghiệm online có khả năng co giãn trên GCP, chứng minh bằng:
- Kiến trúc decouple: API nhận bài trả 202 nhanh + Queue hấp thụ spike + Worker autoscale xử lý chấm điểm
- Load test theo kịch bản spike cuối giờ thi
- Dashboard/metrics: latency, error rate, backlog, autoscaling events
- Demo: submit -> queue -> worker scale out -> kết quả scored

## 1) Kiến trúc chốt
- Cloud Run service A: `exam-api` (HTTP public)  
  - POST submit -> ghi submission status RECEIVED -> publish Pub/Sub -> trả 202 + submissionId  
  - GET submission -> trả trạng thái & điểm
- Pub/Sub topic: `score-jobs`
- Pub/Sub push subscription: `score-jobs-sub` -> push tới Cloud Run service B
- Cloud Run service B: `score-worker` (HTTP endpoint nhận push)  
  - idempotent theo submissionId  
  - chấm điểm -> update DB -> ack (HTTP 2xx)
- Cloud SQL Postgres: lưu exams/questions/submissions/(submission_answers)
- (Optional) Redis cache: cache answer key (để tối ưu, giai đoạn 2)
- Cloud Monitoring/Logging: xem autoscale + backlog + latency

## 2) Mốc công việc (theo tuần / theo buổi)
### Phase 1 — Spec & skeleton (0.5–1 ngày)
- [ ] Chốt spec file: API, DB schema, Pub/Sub contract, scaling/SLO, load test plan
- [ ] Chốt workflow demo + các metric cần chụp hình đưa vào báo cáo

### Phase 2 — Local dev bằng Docker (1–2 ngày)
- [x] Tạo 2 service: `exam-api`, `score-worker`
- [ ] Tạo db schema + migration script
- [x] Docker compose: postgres + exam-api + score-worker
- [ ] Unit test scoring logic (nhỏ thôi)
- [ ] Smoke test local: submit -> worker xử lý -> GET result thấy SCORED

### Phase 3 — Deploy lên GCP “thật” (1–2 ngày)
- [ ] Tạo Artifact Registry
- [ ] Build & push images của 2 service
- [ ] Tạo Cloud SQL Postgres (public IP hoặc connector tuỳ mức)
- [ ] Tạo Secret Manager (DB password, JWT/API key)
- [ ] Deploy Cloud Run `exam-api` (public)
- [ ] Deploy Cloud Run `score-worker` (push endpoint)
- [ ] Tạo Pub/Sub topic + push subscription trỏ vào `score-worker` URL
- [ ] Seed exam data (ít nhất 1 đề 50 câu để demo/load)

### Phase 4 — Load test & Observability (1 ngày)
- [ ] Viết k6 scripts 4 kịch bản: baseline / ramp / spike / fluctuating
- [ ] Chạy test trên `exam-api` URL
- [ ] Chụp dashboard:
  - Cloud Run instances/latency/5xx
  - Pub/Sub backlog + oldest unacked age
  - Cloud SQL CPU + connections
- [ ] Tổng hợp số liệu -> bảng kết quả cho report

### Phase 5 — Demo & report (1–2 ngày)
- [ ] Runbook demo 15 phút
- [ ] Slide: problem -> architecture -> scaling config -> experiments -> results -> lessons learned
- [ ] (Optional) Hardening: push auth bằng OIDC, DLQ, rate limit, Redis cache

## 3) Checklist chức năng tối thiểu (MVP)
- [x] POST /exams/{examId}/submissions trả 202 + submissionId
- [x] GET /submissions/{submissionId} trả status (RECEIVED/SCORING/SCORED/FAILED) + score/total
- [x] Worker xử lý idempotent (Pub/Sub retry không tạo double score)
- [ ] DB schema chạy được
- [ ] Seed 1 exam (>= 30–50 questions)
- [ ] Logging có traceId/submissionId để debug

## 4) Checklist co giãn & đo đạc (bắt buộc để ăn điểm)
- [ ] Spike test: 100 rps baseline -> spike 3000–8000 rps -> back
- [ ] Submit endpoint vẫn ổn (202, 5xx < 1%)
- [ ] Backlog Pub/Sub tăng rồi giảm về ~0
- [ ] `score-worker` scale out rõ (instances tăng mạnh khi backlog tăng)
- [ ] Có số liệu p95/p99 latency của POST /submit
- [ ] Có số liệu “time-to-score” (submit -> SCORED) cho mẫu submissions

## 5) Quyết định kỹ thuật (đã chốt)
- Pub/Sub **push subscription** -> Cloud Run `score-worker`
- Giai đoạn 1: Deploy **thủ công bằng gcloud** (nhanh, chắc pass)
- Terraform để Phase 2 (nếu cần “xịn” hơn)

## 6) Rủi ro & phương án xử lý nhanh
- DB connection bottleneck:
  - giới hạn worker concurrency
  - connection pooling
- Pub/Sub retry tạo duplicate:
  - idempotency theo submissionId + trạng thái SCORED
- Cloud Run timeouts:
  - worker timeout đủ lớn (60–300s)
  - scoring tối ưu (tính nhanh, tránh query nặng)
- UI/metrics thiếu:
  - dùng Cloud Monitoring built-in + log-based metric nếu cần

## 7) Output cuối cùng cần nộp/đem bảo vệ
- Repo code + docs spec
- Script load test (k6)
- Ảnh chụp dashboard + bảng tổng hợp số liệu
- Slide 15 phút + runbook demo