# 📁 Scripts Folder - Test Suite Overview

## ✅ Tổng quan

Folder này chứa **đầy đủ test scripts** để demo **4 chức năng chính** của hệ thống Exam Scoring Cloud cho team.

### 🎯 4 Chức năng được test

| # | Chức năng | Script | Status |
|---|-----------|--------|--------|
| 1 | **Nộp bài tức thì** (Async Submit - 202) | `spike_load_test.py` | ✅ Hoàn thiện |
| 2 | **Chấm điểm tin cậy** (Idempotent, Retry-safe) | `test_idempotency.py` | ✅ Hoàn thiện |
| 3 | **Tra cứu kết quả** (Polling API) | `spike_load_test.py --poll` | ✅ Hoàn thiện |
| 4 | **Dashboard Giám sát** (Realtime Monitoring) | `test_dashboard.py` | ✅ Hoàn thiện |

---

## 📂 Danh sách Files

### 🧪 Test Scripts (Mới tạo)

| File | Mục đích | Độ ưu tiên |
|------|----------|------------|
| **`test_idempotency.py`** | Test chấm điểm tin cậy, không chấm trùng | ⭐⭐⭐ |
| **`test_dashboard.py`** | Test dashboard realtime monitoring | ⭐⭐⭐ |
| **`run_all_tests.sh`** | Chạy tất cả tests một lần | ⭐⭐⭐ |

### 📊 Load Testing Scripts (Có sẵn)

| File | Mục đích | Độ ưu tiên |
|------|----------|------------|
| `spike_load_test.py` | Spike load test + polling | ⭐⭐⭐ |
| `make_load.py` | Load generator cơ bản | ⭐⭐ |
| `demo_spike.py` | Demo spike scenario | ⭐⭐ |
| `bulk_submit.py` | Submit tuần tự đơn giản | ⭐ |

### 📖 Documentation

| File | Mục đích |
|------|----------|
| **`DEMO_GUIDE.md`** | Hướng dẫn demo chi tiết cho team (10-15 phút) |
| **`QUICK_REFERENCE.md`** | Quick reference commands |
| `README.md` | File này |

---

## 🚀 Quick Start (Cho Team Demo)

### Option 1: Chạy tất cả tests (Recommended)

```bash
# Chạy full test suite
./run_all_tests.sh

# Kết quả sẽ lưu vào folder test_results_YYYYMMDD_HHMMSS/
```

### Option 2: Chạy từng test riêng lẻ

```bash
# Test 1: Dashboard monitoring
python3 test_dashboard.py --live-demo

# Test 2: Idempotency
python3 test_idempotency.py

# Test 3: Spike load + polling
python3 spike_load_test.py --count 1000 --poll
```

---

## 📊 Test Coverage Matrix

| Chức năng | Test Case | Script | Kết quả mong đợi |
|-----------|-----------|--------|------------------|
| **Async Submit** | 1000 concurrent submissions | `spike_load_test.py` | 100% success, P95 < 100ms |
| **Idempotency** | Sequential duplicates | `test_idempotency.py` | Same submissionId returned |
| **Idempotency** | Concurrent duplicates | `test_idempotency.py` | No race condition |
| **Idempotency** | Retry simulation | `test_idempotency.py` | Consistent results |
| **Idempotency** | Deterministic scoring | `test_idempotency.py` | Same answers = same score |
| **Polling API** | Status transitions | `spike_load_test.py --poll` | RECEIVED → SCORING → SCORED |
| **Dashboard** | Stats API connectivity | `test_dashboard.py` | 200 OK |
| **Dashboard** | Realtime metrics update | `test_dashboard.py` | Updates every 2s |
| **Dashboard** | Submission feed | `test_dashboard.py` | Shows recent submissions |
| **Dashboard** | Autoscaling metrics | `test_dashboard.py` | Instances, CPU, Memory |
| **Dashboard** | Backlog monitoring | `test_dashboard.py` | Tracks queue size |
| **Dashboard** | Throughput calculation | `test_dashboard.py` | Accurate req/min |
| **Dashboard** | Exam management | `test_dashboard.py` | Lists all exams |

**Tổng cộng:** 13 test cases covering 4 core functionalities ✅

---

## 🎬 Demo Flow (15 phút)

### Chuẩn bị (2 phút)
```bash
# 1. Start services
cd /root/IT5404---Cloud-computing/xam-scoring-cloud
docker-compose up -d

# 2. Verify services
docker-compose ps

# 3. Open dashboard
# Browser: http://localhost:8000/admin-dashboard.html
```

### Demo (10 phút)
```bash
# 4. Run full test suite
cd scripts
./run_all_tests.sh
```

### Review (3 phút)
```bash
# 5. Show results
cat test_results_*/SUMMARY.txt

# 6. Show dashboard metrics
# Browser: Refresh dashboard to see final state
```

---

## 📈 Expected Results

### ✅ All Tests Should PASS

```
Dashboard Test:        ✓ 7/7 tests passed
Idempotency Test:      ✓ 4/4 tests passed
Spike Load Test:       ✓ 100% success rate

Overall: ALL TESTS PASSED ✓
```

### 📊 Performance Metrics

```
Spike Load Test:
- Total Submissions: 500
- Success Rate: 100%
- Avg Response Time: ~50ms
- P95 Response Time: ~80ms
- Throughput: ~125 req/s

Idempotency Test:
- No duplicate scoring detected
- Consistent results across retries
- Deterministic scoring verified

Dashboard Test:
- Realtime updates: ✓
- Metrics accuracy: ✓
- Feed updates: ✓
```

---

## 🔧 Troubleshooting

### Services không chạy
```bash
docker-compose up -d
docker-compose ps
```

### API không accessible
```bash
curl -H "X-API-KEY: change-me" http://localhost:8080/v1/internal/stats
```

### Tests fail
```bash
# Check logs
cat test_results_*/dashboard_test.log
cat test_results_*/idempotency_test.log
cat test_results_*/spike_test.log
```

---

## 📚 Documentation

- **Chi tiết demo:** Xem `DEMO_GUIDE.md`
- **Quick commands:** Xem `QUICK_REFERENCE.md`
- **System architecture:** Xem `../README.md`

---

## 🎯 Key Takeaways cho Team

1. ✅ **Async Submit:** Client nhận 202 ngay lập tức, không chờ chấm điểm
2. ✅ **Idempotency:** Worker retry-safe, không bao giờ chấm trùng
3. ✅ **Polling API:** Client chủ động lấy kết quả khi cần
4. ✅ **Dashboard:** Giám sát realtime, dễ debug, dễ scale

**Kết luận:** Hệ thống đáp ứng đầy đủ 4 yêu cầu chức năng! 🎉

---

## 📞 Support

Nếu có vấn đề khi chạy tests, check:
1. Services running: `docker-compose ps`
2. API accessible: `curl http://localhost:8080/v1/internal/stats`
3. Logs: `docker-compose logs -f`
4. Test logs: `cat test_results_*/SUMMARY.txt`
