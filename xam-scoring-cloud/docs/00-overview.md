# Online Exam Scoring System (Elastic on GCP)

## Mục tiêu
Xây dựng hệ thống chấm điểm thi trắc nghiệm trực tuyến có khả năng co giãn trên Google Cloud, chịu được tải tăng đột biến cuối giờ thi.

## Bài toán
- Nhiều sinh viên nộp bài trong thời gian ngắn (spike traffic).
- Mỗi submission cần: validate -> chấm điểm -> lưu kết quả.
- Yêu cầu: không sập, độ trễ thấp cho submit, xử lý chấm điểm ổn định, tự động scale.

## Giải pháp tổng quan (cloud-native)
- Cloud Run `exam-api`: nhận bài và đẩy job vào Pub/Sub (trả 202 ngay).
- Pub/Sub `score-jobs`: hàng đợi hấp thụ spike.
- Cloud Run `score-worker`: tiêu thụ job, chấm điểm, ghi Cloud SQL.
- Cloud SQL (PostgreSQL): lưu exam, question, submission, result.
- Cloud Monitoring/Logging: đo latency, error rate, backlog, scale events.

## Deliverables
- Kiến trúc + spec API + schema DB + contract message
- Kịch bản load test (baseline/ramp/spike/fluctuating) + metric báo cáo
- Runbook demo bảo vệ