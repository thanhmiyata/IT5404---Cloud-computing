# Monitoring Dashboard Specification

Hệ thống Dashboard giám sát thời gian thực cho kỳ thi trực tuyến (xam-scoring-cloud).

## 1. Tổng quan thiết kế
Dashboard được thiết kế theo phong cách **Cloud-Native Command Center**:
- **Giao diện**: Dark mode (Nền #0f172a), phông chữ Inter/Roboto.
- **Thành phần**: Sử dụng Glassmorphism (độ mờ nền) và các thành phần thẻ (cards) bo góc.
- **Tính năng**: Tự động cập nhật số liệu mỗi 5-10 giây hoặc qua WebSocket (nếu có).

## 2. Các chỉ số chính (Key Metrics)

### A. Business Metrics
- **Total Submissions**: Tổng số bài đã nhận vào hệ thống.
- **Queue Status (Backlog)**: Số lượng message đang đợi trong Pub/Sub (Chỉ số quan trọng nhất để thấy sự nghẽn cổ chai).
- **Processing (Scoring)**: Số lượng worker đang xử lý đồng thời.
- **Completion Rate**: Tỷ lệ bài đã chấm xong (Status: SCORED).

### B. Infrastructure Metrics
- **Cloud Run Instance Count**: Số lượng container đang chạy cho `exam-api` và `score-worker`. Chứng minh khả năng **Autoscaling**.
- **CPU/Memory Usage**: Tải trung bình của hệ thống worker.
- **Cloud SQL Connections**: Số lượng kết nối vào database.

### C. Performance Metrics
- **API Latency (p95)**: Thời gian phản hồi của endpoint `/submit`.
- **E2E Latency**: Thời gian từ lúc nộp bài đến khi có kết quả.
- **Throughput (RPS)**: Số lượng request mỗi giây từ k6 load test.

## 3. Bản đồ giao diện (Layout Map)
| Cột 1 (Sidebar) | Cột 2 (Main Center) | Cột 3 (Right Panel) |
| :--- | :--- | :--- |
| Navigation | **Top Row**: 4 Summary Cards (Totals) | **System Health**: CPU/RAM Gauges |
| Filters (Exam ID) | **Middle**: Scaling Chart (Instances vs Time) | **Live Logs**: Scrolling feed |
| Auth Status | **Bottom**: Latency & Backlog Chart | **Alerts**: Queue thresholds |

## 4. Công nghệ triển khai (Đề xuất)
- **Frontend**: React.js / Vite.
- **Styling**: Tailwind CSS + Framer Motion.
- **Charts**: Recharts (Dễ tuỳ chỉnh kiểu dashboard).
- **Icons**: Lucide React.
