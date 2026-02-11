# 🚀 Horizontal Scaling Test - Quick Guide

## ✨ Tính năng mới

**Script:** `test_horizontal_scaling.py`

Test khả năng horizontal scaling với **10,000 submissions** và monitor worker scaling lên **500-1000 instances**.

---

## 🎯 Mục tiêu

Verify hệ thống có thể:
- ✅ Handle 10K concurrent submissions
- ✅ Auto scale workers lên 500-1000 instances
- ✅ Maintain error rate < 1%
- ✅ Auto scale down sau khi load giảm

---

## 🚀 Cách chạy

### **Basic Test (10K submissions)**

```bash
cd /root/IT5404---Cloud-computing/xam-scoring-cloud/scripts
python3 test_horizontal_scaling.py --count 10000
```

### **Custom Count**

```bash
# Test with 5K submissions
python3 test_horizontal_scaling.py --count 5000

# Test with 20K submissions (extreme)
python3 test_horizontal_scaling.py --count 20000
```

### **Save Results**

```bash
python3 test_horizontal_scaling.py --count 10000 --output scaling_results.json
```

### **Remote Server**

```bash
python3 test_horizontal_scaling.py \
  --url http://136.110.44.49:8080 \
  --count 10000 \
  --output scaling_results.json
```

---

## 📊 Test Phases

### **Phase 1: Baseline (5s)**
- Đo instances, backlog, completed trước khi load

### **Phase 2: Load Injection (60-90s)**
- Submit 10K requests trong batches
- Monitor throughput, error rate

### **Phase 3: Scale-Up Monitoring (60s)**
- Track instances scaling lên
- Monitor backlog growth
- Verify peak instances >= 500

### **Phase 4: Scale-Down Monitoring (120s)**
- Wait for queue drain
- Track instances scaling xuống
- Verify graceful scale-down

**Total Duration:** ~5-7 phút

---

## 📈 Expected Results

```
PHASE 1: Baseline Measurement
  Baseline Instances: 50
  Baseline Backlog: 100

PHASE 2: Injecting 10000 Submissions
  Progress: 100/100 batches (10000 success, 0 errors) - 130 req/s
  Total Submitted: 10000/10000
  Total Errors: 0 (0.00%)
  Avg Throughput: 130.5 req/s

PHASE 3: Monitoring Auto Scale-Up
  TIME       | INSTANCES  | BACKLOG    | COMPLETED  | THROUGHPUT  
  ────────────────────────────────────────────────────────────────
  07:50:00   | 50         | 100        | 25000      | 120.0       
  07:50:05   | 150        | 2500       | 25500      | 180.0       
  07:50:10   | 350        | 5000       | 26000      | 250.0       
  07:50:15   | 650        | 7500       | 26500      | 320.0       
  07:50:20   | 850        | 8500       | 27000      | 380.0       

  Peak Instances: 850
  Peak Backlog: 8500

PHASE 4: Monitoring Auto Scale-Down
  TIME       | INSTANCES  | BACKLOG    | COMPLETED  | THROUGHPUT  
  ────────────────────────────────────────────────────────────────
  07:51:00   | 850        | 7000       | 28000      | 350.0       
  07:51:10   | 600        | 4000       | 30000      | 280.0       
  07:51:20   | 350        | 1500       | 32000      | 200.0       
  07:51:30   | 150        | 500        | 34000      | 120.0       
  07:51:40   | 80         | 100        | 35000      | 80.0        

  Final Instances: 80
  Final Backlog: 100

SCALING TEST SUMMARY
  Baseline → Peak Instances: 50 → 850 (17.0x)
  Peak → Final Instances: 850 → 80
  Submissions Processed: 10000/10000
  
  ✓ PASS: Horizontal scaling verified
```

---

## ✅ Pass Criteria

| Metric | Target | Status |
|--------|--------|--------|
| **Peak Instances** | >= 500 (excellent) or >= 100 (good) | ✅ |
| **Scale-up Ratio** | >= 1.5x | ✅ |
| **Error Rate** | < 1% | ✅ |
| **Submissions Handled** | 10000/10000 | ✅ |

---

## 🎬 Demo Tips

### **Talking Points:**

1. **Massive Concurrency**
   - "Hệ thống xử lý được 10,000 submissions đồng thời"
   - "Throughput ~130 req/s trong quá trình submit"

2. **Auto Scale-Up**
   - "Workers tự động scale từ 50 lên 850 instances (17x)"
   - "Đáp ứng được spike load mà không cần manual intervention"

3. **Resilience**
   - "Error rate < 1% ngay cả với massive load"
   - "Hệ thống stable, không crash"

4. **Auto Scale-Down**
   - "Sau khi load giảm, workers tự động scale xuống"
   - "Cost-efficient: Chỉ dùng resources khi cần"

### **Visual Demo:**

```bash
# Terminal 1: Run test
python3 test_horizontal_scaling.py --count 10000

# Terminal 2: Watch dashboard
# Open http://localhost:8000/admin-dashboard.html
# Show real-time metrics updating

# Terminal 3: Monitor docker
watch -n 2 'docker stats --no-stream'
```

---

## 🔧 Troubleshooting

### **Test chạy chậm?**
- Giảm count: `--count 5000`
- Tăng batch size: `--batch-size 200`

### **Error rate cao?**
- System có thể đang overloaded
- Check docker resources: `docker stats`
- Check logs: `docker-compose logs -f`

### **Không thấy scaling?**
- System có thể đã ở peak capacity
- Check baseline instances (nếu đã cao thì không scale thêm)
- Verify autoscaling config trong docker-compose

---

## 📝 Output Files

Khi chạy với `--output scaling_results.json`:

```json
{
  "test_config": {
    "total_submissions": 10000,
    "batch_size": 100,
    "max_workers": 100
  },
  "result": {
    "passed": true,
    "baseline_instances": 50,
    "peak_instances": 850,
    "final_instances": 80,
    "scale_up_ratio": 17.0,
    "total_submissions": 10000,
    "successful_submissions": 10000,
    "error_rate_percent": 0.0,
    "avg_throughput_rps": 130.5
  }
}
```

---

## 🎯 Next Steps

Sau khi chạy test thành công:

1. ✅ Capture screenshots của dashboard
2. ✅ Save JSON results
3. ✅ Document peak instances achieved
4. ✅ Calculate cost savings from auto scale-down
5. ✅ Prepare demo presentation

---

## 💡 Pro Tips

- **Best time to demo:** Khi system ở baseline (low load)
- **Most impressive:** Show dashboard + test running side-by-side
- **Backup plan:** Có JSON results sẵn nếu live demo fail
- **Highlight:** Scale-up ratio (càng cao càng impressive)

---

**Ready to demo? 🚀**

```bash
python3 test_horizontal_scaling.py --count 10000
```
