# 🎯 Quick Reference - Test Commands

## 🚀 One-Command Full Demo

```bash
# Chạy TẤT CẢ tests một lần (recommended cho demo)
./run_all_tests.sh

# Chạy với remote server
./run_all_tests.sh http://136.110.44.49:8080 change-me
```

---

## 📝 Individual Tests

### 1️⃣ Async Submit Test
```bash
# Quick test (100 submissions)
python3 spike_load_test.py --count 100

# Full spike test (1000 submissions)
python3 spike_load_test.py --count 1000 --workers 100

# With result polling
python3 spike_load_test.py --count 500 --poll --poll-timeout 120
```

### 2️⃣ Idempotency Test
```bash
# Run all idempotency tests
python3 test_idempotency.py

# Save results
python3 test_idempotency.py --output results.json
```

### 3️⃣ Dashboard Test
```bash
# Basic dashboard test
python3 test_dashboard.py

# With live monitoring demo
python3 test_dashboard.py --live-demo --duration 60
```

### 4️⃣ Bulk Submit (Simple)
```bash
# Submit 30 exams sequentially
python3 bulk_submit.py
```

---

## 🎬 Demo Scenarios

### Scenario A: Quick 5-min Demo
```bash
# 1. Show dashboard
open http://localhost:8000/admin-dashboard.html

# 2. Run quick spike test
python3 spike_load_test.py --count 200 --workers 50

# 3. Show idempotency
python3 test_idempotency.py
```

### Scenario B: Full 15-min Demo
```bash
# Run everything
./run_all_tests.sh
```

### Scenario C: Live Monitoring Demo
```bash
# Terminal 1: Dashboard
open http://localhost:8000/admin-dashboard.html

# Terminal 2: Live monitoring
python3 test_dashboard.py --live-demo --duration 120

# Terminal 3: Create load
python3 spike_load_test.py --count 1000 --workers 100
```

---

## 🔍 Verify Results

```bash
# Check API health
curl -H "X-API-KEY: change-me" http://localhost:8080/v1/internal/stats | jq

# Check specific submission
curl -H "X-API-KEY: change-me" http://localhost:8080/v1/submissions/{ID} | jq

# View test results
cat test_results_*/SUMMARY.txt
```

---

## 📊 Expected Results

| Test | Success Criteria |
|------|------------------|
| **Spike Load** | 100% success rate, P95 < 100ms, throughput > 100 req/s |
| **Idempotency** | All 4 tests PASS, no duplicate scoring |
| **Dashboard** | All 7 tests PASS, metrics update every 2s |
| **Polling** | All submissions reach SCORED status within timeout |

---

## 🐛 Quick Troubleshooting

```bash
# Services not running?
cd /root/IT5404---Cloud-computing/xam-scoring-cloud
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f

# Restart everything
docker-compose restart
```

---

## 💡 Pro Tips

1. **Always check services first:** `docker-compose ps`
2. **Open dashboard before running tests** to see realtime updates
3. **Use `--output` flag** to save results for later analysis
4. **Run `./run_all_tests.sh`** for comprehensive demo
5. **Check `test_results_*` folders** for detailed logs

---

## 📞 Help

For detailed guide: `cat DEMO_GUIDE.md`
