# 🧪 Test Scripts - Demo Guide

Folder này chứa các test scripts để demo đầy đủ 4 chức năng chính của hệ thống cho team.

## 📋 Danh sách Test Scripts

| Script | Chức năng test | Mục đích |
|--------|---------------|----------|
| `spike_load_test.py` | ✅ Async Submit (202) | Test nộp bài tức thì, không chờ chấm điểm |
| `test_idempotency.py` | ✅ Chấm điểm tin cậy | Test idempotency, retry-safe, không chấm trùng |
| `test_dashboard.py` | ✅ Dashboard Giám sát | Test realtime metrics, logs, autoscaling |
| `bulk_submit.py` | ✅ Tra cứu kết quả | Test polling API để lấy điểm |

---

## 🎯 Kịch bản Demo cho Team

### **Demo 1: Nộp bài tức thì (Async Submit)**

**Mục tiêu:** Chứng minh API trả về 202 ngay lập tức, không chờ chấm điểm

```bash
# Test 1000 submissions đồng thời
python3 scripts/spike_load_test.py --count 1000 --workers 100

# Kết quả mong đợi:
# - Tất cả requests nhận 202 Accepted
# - Response time < 100ms (P95)
# - Throughput > 500 req/s
```

**Điểm nhấn khi demo:**
- ✅ Client không phải chờ worker chấm điểm
- ✅ Hệ thống chấp nhận burst traffic (1000 requests cùng lúc)
- ✅ Response time nhanh và ổn định

---

### **Demo 2: Chấm điểm tin cậy (Idempotency)**

**Mục tiêu:** Chứng minh worker không chấm trùng khi có retry

```bash
# Chạy full test suite idempotency
python3 scripts/test_idempotency.py

# Test với remote server
python3 scripts/test_idempotency.py --url http://136.110.44.49:8080

# Lưu kết quả
python3 scripts/test_idempotency.py --output idempotency_results.json
```

**Các test case:**
1. ✅ **Sequential Duplicates:** Nộp cùng 1 bài 5 lần → chỉ chấm 1 lần
2. ✅ **Concurrent Duplicates:** 10 requests đồng thời → không race condition
3. ✅ **Retry Simulation:** Fetch cùng 1 submission 20 lần → kết quả nhất quán
4. ✅ **Deterministic Scoring:** Cùng đáp án → cùng điểm số

**Điểm nhấn khi demo:**
- ✅ Không bao giờ chấm trùng (idempotent)
- ✅ Xử lý race condition tốt
- ✅ Retry-safe (worker có thể retry mà không sợ lỗi)

---

### **Demo 3: Tra cứu kết quả (Polling API)**

**Mục tiêu:** Client có thể polling để lấy điểm sau khi nộp

```bash
# Test với polling enabled
python3 scripts/spike_load_test.py --count 100 --poll --poll-timeout 60

# Kết quả mong đợi:
# - Tất cả submissions chuyển từ RECEIVED → SCORING → SCORED
# - Có thể lấy điểm qua API /v1/submissions/{id}
```

**Flow demo:**
1. Submit bài thi → nhận `submissionId`
2. Poll `/v1/submissions/{submissionId}` mỗi 2s
3. Khi `status = SCORED` → hiển thị điểm

**Điểm nhấn khi demo:**
- ✅ Client chủ động polling (không cần webhook)
- ✅ Status transitions rõ ràng: RECEIVED → SCORING → SCORED
- ✅ API trả về đầy đủ: score, total, breakdown

---

### **Demo 4: Dashboard Giám sát (Real-time Monitoring)**

**Mục tiêu:** Dashboard hiển thị realtime metrics từ Database

#### **Bước 1: Mở Dashboard**
```bash
# Truy cập dashboard trong browser
http://localhost:8000/admin-dashboard.html

# Hoặc remote
http://136.110.44.49:8000/admin-dashboard.html
```

#### **Bước 2: Chạy test dashboard**
```bash
# Test connectivity và metrics
python3 scripts/test_dashboard.py

# Test với live monitoring demo
python3 scripts/test_dashboard.py --live-demo --duration 60

# Test remote server
python3 scripts/test_dashboard.py --url http://136.110.44.49:8080
```

**Các test case:**
1. ✅ **Dashboard Connectivity:** API `/v1/internal/stats` hoạt động
2. ✅ **Real-time Metrics:** Metrics update mỗi 2s
3. ✅ **Submission Feed:** Hiển thị bài nộp gần đây
4. ✅ **Autoscaling Metrics:** Hiển thị instances, CPU, memory
5. ✅ **Backlog Monitoring:** Track queue backlog realtime
6. ✅ **Throughput Calculation:** Tính throughput/latency chính xác
7. ✅ **Exam Management:** Hiển thị danh sách đề thi

#### **Bước 3: Tạo load để xem dashboard update**
```bash
# Terminal 1: Mở dashboard trong browser
# Terminal 2: Tạo load
python3 scripts/spike_load_test.py --count 500 --workers 50

# Quan sát dashboard:
# - Backlog tăng lên
# - Instances scale up
# - Throughput tăng
# - Submission feed update realtime
```

**Điểm nhấn khi demo:**
- ✅ Metrics update realtime (mỗi 2s)
- ✅ Chart hiển thị autoscaling behavior
- ✅ Logs/feed hiển thị submissions mới nhất
- ✅ Infrastructure metrics (CPU, memory, instances)

---

## 🚀 Kịch bản Demo Tổng hợp (Full Flow)

**Thời lượng:** 10-15 phút

### **Setup (1 phút)**
```bash
# Terminal 1: Start services
cd xam-scoring-cloud
docker-compose up -d

# Terminal 2: Start dashboard
python3 -m http.server 8000

# Terminal 3: Mở browser
# → http://localhost:8000/admin-dashboard.html
```

### **Demo Flow (10 phút)**

#### **1. Baseline (1 phút)**
- Mở dashboard, show metrics ban đầu (backlog = 0, instances = 1)

#### **2. Async Submit Test (2 phút)**
```bash
# Terminal 3
python3 scripts/spike_load_test.py --count 1000 --workers 100
```
- **Giải thích:** 1000 students nộp bài cùng lúc khi hết giờ thi
- **Quan sát:** Tất cả nhận 202 Accepted trong < 10s
- **Dashboard:** Backlog tăng lên 1000

#### **3. Autoscaling & Processing (3 phút)**
- **Quan sát dashboard:**
  - Instances scale from 1 → 3-5
  - Backlog giảm dần
  - Throughput tăng lên
  - Submission feed update realtime

#### **4. Idempotency Test (2 phút)**
```bash
# Terminal 3
python3 scripts/test_idempotency.py
```
- **Giải thích:** Test xem có chấm trùng không
- **Kết quả:** All tests PASS ✅

#### **5. Dashboard Test (2 phút)**
```bash
# Terminal 3
python3 scripts/test_dashboard.py --live-demo
```
- **Giải thích:** Verify dashboard metrics chính xác
- **Kết quả:** All tests PASS ✅

---

## 📊 Kết quả mong đợi

### **Spike Load Test**
```
Total Submissions: 1000
Successful: 1000 (100%)
Failed: 0 (0%)

Response Time:
  Average: 45.2ms
  P95: 78.5ms
  P99: 95.3ms

Throughput: 125.5 submissions/sec
```

### **Idempotency Test**
```
✓ PASS - Sequential Duplicate Submissions
✓ PASS - Concurrent Duplicate Submissions
✓ PASS - Worker Retry Simulation
✓ PASS - Deterministic Scoring

Overall Result: ALL TESTS PASSED ✓
```

### **Dashboard Test**
```
✓ PASS - Dashboard Connectivity
✓ PASS - Real-time Metrics Update
✓ PASS - Submission Feed Updates
✓ PASS - Autoscaling Metrics
✓ PASS - Backlog Monitoring
✓ PASS - Throughput Calculation
✓ PASS - Exam Management Data

Overall Result: ALL TESTS PASSED ✓
```

---

## 🎬 Tips cho Demo thành công

### **Trước khi demo:**
1. ✅ Kiểm tra services đang chạy: `docker-compose ps`
2. ✅ Test API connectivity: `curl http://localhost:8080/health`
3. ✅ Mở dashboard trước để team thấy baseline
4. ✅ Chuẩn bị 3 terminals: services, dashboard, tests

### **Trong khi demo:**
1. ✅ Giải thích mục đích của từng test
2. ✅ Cho team thấy dashboard update realtime
3. ✅ Highlight các con số quan trọng (P95, throughput, success rate)
4. ✅ Show logs nếu có lỗi để prove transparency

### **Sau khi demo:**
1. ✅ Lưu kết quả test ra JSON: `--output results.json`
2. ✅ Show metrics cuối cùng trên dashboard
3. ✅ Giải thích architecture (API → Pub/Sub → Worker → DB)

---

## 🐛 Troubleshooting

### **Lỗi: Connection refused**
```bash
# Check services
docker-compose ps

# Restart nếu cần
docker-compose restart
```

### **Lỗi: Dashboard không update**
```bash
# Check stats API
curl -H "X-API-KEY: change-me" http://localhost:8080/v1/internal/stats

# Check browser console (F12) for errors
```

### **Lỗi: Tests fail**
```bash
# Check API key
export API_KEY="change-me"

# Check firewall (nếu remote)
# GCP: Allow TCP 8080, 8000
```

---

## 📝 Checklist Demo

- [ ] Services running (`docker-compose ps`)
- [ ] Dashboard accessible (browser)
- [ ] Terminal windows ready (3 terminals)
- [ ] Test scripts executable (`chmod +x scripts/*.py`)
- [ ] API key configured
- [ ] Network/firewall OK (if remote)
- [ ] Browser DevTools open (F12) để show realtime updates
- [ ] Screen recording ready (optional)

---

## 🎯 Key Messages cho Team

1. **Async Submit:** Client không bị block, UX tốt hơn
2. **Idempotency:** Worker retry-safe, không sợ chấm trùng
3. **Polling API:** Client chủ động lấy kết quả
4. **Dashboard:** Giám sát realtime, dễ debug, dễ scale

**Kết luận:** Hệ thống đáp ứng đầy đủ 4 yêu cầu chức năng! ✅
