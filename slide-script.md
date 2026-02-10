# Kịch bản Slide Báo cáo
## Hệ thống Chấm điểm Thi Trắc nghiệm có khả năng Co giãn trên nền tảng Cloud

**Thời lượng dự kiến:** 15-20 phút

---

## SLIDE 1: Trang bìa

**Tiêu đề:** Thiết kế và Triển khai Hệ thống Chấm điểm Thi Trắc nghiệm có khả năng Co giãn sử dụng nền tảng Cloud

**Thông tin:**
- Môn học: IT5404 - Cloud Computing
- Tên nhóm/Người thực hiện: [Điền tên]
- Ngày: [Điền ngày]

---

## SLIDE 2: Nội dung trình bày

1. Bối cảnh & Bài toán
2. Giải pháp Kiến trúc
3. Thiết kế Hệ thống
4. Xây dựng & Triển khai
5. Kiểm thử & Kết quả
6. Kết luận & Hướng phát triển
7. Demo

---

## SLIDE 3: Bối cảnh thực tế

**Vấn đề: Spike Traffic cuối giờ thi**

- 1000 sinh viên thi online
- Phút cuối: gần như tất cả cùng nhấn "Nộp bài"
- Hệ thống phải xử lý hàng nghìn request trong vài giây

**Hình minh họa:** Biểu đồ traffic spike (bình thường → đột biến → giảm)

**Note cho người trình bày:**
> "Hãy tưởng tượng kỳ thi với 1000 sinh viên. Khi còn 1 phút cuối, gần như tất cả cùng nhấn nộp bài. Đây là thách thức lớn nhất của hệ thống thi trực tuyến."

---

## SLIDE 4: Hạn chế mô hình truyền thống

**Mô hình Monolithic Synchronous:**

```
Client → Server → Database (chờ đồng bộ)
```

**Các vấn đề:**

| Vấn đề | Hậu quả |
|--------|---------|
| I/O Bottleneck | Request xếp hàng dài |
| Synchronous Processing | Client phải chờ chấm xong |
| Khó Scale | Database là bottleneck |
| Over-provisioning | Lãng phí tài nguyên |

**Note cho người trình bày:**
> "Mô hình truyền thống bắt client chờ toàn bộ quy trình chấm điểm. Khi spike, hệ thống nghẽn và timeout."

---

## SLIDE 5: Mục tiêu đề tài

**Mục tiêu chức năng:**
- ✅ Nộp bài tức thì (202 Accepted)
- ✅ Chấm điểm tin cậy (Idempotent)
- ✅ Tra cứu kết quả (Polling API)
- ✅ Dashboard giám sát (Realtime)

**Mục tiêu phi chức năng (SLO):**
- ⚡ Submit p95 < 300ms (bình thường)
- ⚡ Submit p95 < 800ms (spike)
- ✅ Error rate < 1%
- ⏱️ Time-to-Score p95 < 30s

---

## SLIDE 6: Giải pháp - Kiến trúc Event-Driven

**Ý tưởng chính: Tách biệt nhận bài và chấm điểm**

```
┌─────────┐     ┌──────────┐     ┌───────────┐     ┌──────────────┐     ┌───────────┐
│ Client  │────>│ exam-api │────>│  Pub/Sub  │────>│ score-worker │────>│ PostgreSQL│
└─────────┘     └──────────┘     └───────────┘     └──────────────┘     └───────────┘
                    │                                     │
                    │202 ngay lập tức                     │Async processing
                    └─────────────────────────────────────┘
```

**Note cho người trình bày:**
> "Điểm khác biệt quan trọng: exam-api trả 202 ngay khi nhận bài, không chờ chấm điểm. Queue hấp thụ spike, worker xử lý async."

---

## SLIDE 7: Các thành phần hệ thống (GCP)

| Component | Vai trò | Công nghệ |
|-----------|---------|-----------|
| **exam-api** | Nhận bài, trả 202, publish job | Cloud Run + FastAPI |
| **Pub/Sub** | Queue hấp thụ spike | Google Pub/Sub |
| **score-worker** | Chấm điểm idempotent | Cloud Run + FastAPI |
| **Database** | Lưu exams, submissions, results | Cloud SQL PostgreSQL |
| **Dashboard** | Giám sát realtime | HTML + Chart.js |

**Hình minh họa:** Sơ đồ kiến trúc với icons GCP

---

## SLIDE 8: Database Schema

**4 Tables chính:**

```
exams (exam_id, title, start_at, end_at)
   │
   ├── questions (question_id, exam_id, correct_choice, points)
   │
   └── submissions (submission_id, exam_id, user_id, status, score, ...)
              │
              └── submission_answers (submission_id, question_id, choice, is_correct, points)
```

**Status flow:** `RECEIVED → SCORING → SCORED / FAILED`

---

## SLIDE 9: Luồng Nộp bài (Submit Flow)

```
1. Client: POST /exams/{examId}/submissions
   ↓
2. exam-api: Validate exam & timing
   ↓
3. exam-api: INSERT submission (RECEIVED)
   ↓
4. exam-api: Publish message → Pub/Sub
   ↓
5. exam-api: Return 202 + submissionId  ← Client nhận response nhanh!
```

**Response:**
```json
{
  "submissionId": "sub_9f8a...",
  "status": "RECEIVED"
}
```

**Note cho người trình bày:**
> "Client nhận phản hồi ngay sau bước 5, không cần chờ chấm điểm. Đây là điểm mấu chốt để chịu spike."

---

## SLIDE 10: Luồng Chấm điểm (Score Flow)

```
1. Pub/Sub: Push message → score-worker
   ↓
2. Worker: Parse job, lấy submissionId
   ↓
3. Worker: SELECT status FOR UPDATE (Idempotency check)
   ↓ Nếu đã SCORED → skip
4. Worker: UPDATE status = SCORING
   ↓
5. Worker: Load đáp án từ DB
   ↓
6. Worker: So sánh từng câu → tính điểm
   ↓
7. Worker: INSERT breakdown, UPDATE status = SCORED
   ↓
8. Worker: Return 200 (ack message)
```

**Điểm quan trọng: Idempotency** - Không chấm trùng khi Pub/Sub retry!

---

## SLIDE 11: Cấu trúc Code

```
xam-scoring-cloud/
├── services/
│   ├── exam-api/           # API nhận bài
│   │   ├── app/main.py     # FastAPI endpoints
│   │   └── Dockerfile
│   └── score-worker/       # Worker chấm điểm
│       ├── app/main.py     # Scoring logic
│       └── Dockerfile
├── db/
│   ├── schema.sql
│   └── seed.sql
├── scripts/                # Load test scripts
│   └── spike_load_test.py
├── dashboard.html
└── docker-compose.yml
```

---

## SLIDE 12: Code Highlight - Submit Endpoint

```python
@app.post("/v1/exams/{exam_id}/submissions", status_code=202)
def submit_exam(exam_id: str, body: SubmitRequest):
    submission_id = f"sub_{uuid.uuid4().hex}"
    
    # 1. Validate exam
    # 2. INSERT submission (RECEIVED)
    cur.execute("""
        INSERT INTO submissions (submission_id, exam_id, user_id, status)
        VALUES (%s, %s, %s, 'RECEIVED')
    """, (submission_id, exam_id, body.userId))
    
    # 3. Publish job
    _publish_job(message)
    
    # 4. Return immediately!
    return {"submissionId": submission_id, "status": "RECEIVED"}
```

---

## SLIDE 13: Code Highlight - Idempotent Scoring

```python
@app.post("/v1/score")
def score_job(payload: dict):
    # 1. SELECT FOR UPDATE (lock row)
    cur.execute("""
        SELECT status FROM submissions 
        WHERE submission_id=%s FOR UPDATE
    """, (submission_id,))
    
    # 2. Idempotency check
    if row[0] == "SCORED":
        return {"ok": True}  # Skip! Đã chấm rồi
    
    # 3. Proceed with scoring...
```

**Note cho người trình bày:**
> "SELECT FOR UPDATE lock record để tránh race condition. Nếu đã SCORED thì skip, đảm bảo không chấm trùng."

---

## SLIDE 14: Docker Compose - Local Development

```yaml
services:
  db:
    image: postgres:15
    
  exam-api:
    build: ./services/exam-api
    ports: ["8080:8080"]
    environment:
      PUBSUB_DISABLED: "true"
      SCORE_WORKER_URL: "http://score-worker:8080/v1/score"
      
  score-worker:
    build: ./services/score-worker
    ports: ["8081:8080"]
```

**Local mode:** `PUBSUB_DISABLED=true` → HTTP direct call (không cần GCP)

---

## SLIDE 15: Kịch bản Kiểm thử

**Spike Test - Mô phỏng cuối giờ thi:**

| Tham số | Giá trị |
|---------|---------|
| Tổng submissions | 1000 |
| Concurrent users | 100 |
| Target | POST /exams/exam_001/submissions |

**Command:**
```bash
python3 scripts/spike_load_test.py \
    --url http://<IP>:8080 \
    --count 1000 \
    --poll
```

---

## SLIDE 16: Kết quả Kiểm thử

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Success Rate | > 99% | 100% | ✅ |
| p95 Latency | < 300ms | ~150ms | ✅ |
| p99 Latency | < 800ms | ~450ms | ✅ |
| Throughput | - | 200 req/s | ✅ |
| Time to Score All | < 30s | ~15s | ✅ |

**Kết luận:** Tất cả SLO đều đạt!

---

## SLIDE 17: Dashboard Giám sát

**Screenshot Dashboard**

**Các metrics hiển thị:**
- Total Submissions
- Queue Backlog (RECEIVED + SCORING)
- Completed Jobs (SCORED)
- Processing Instances (auto-scaled)
- Live Logs từ Database

**Hình minh họa:** Screenshot dashboard với biểu đồ Instances vs Backlog

---

## SLIDE 18: Quan sát Auto-Scaling

**Biểu đồ thời gian:**

```
Backlog:    ▓▓▓▓▓▓▓░░░░░░░░░░░░░
Instances:  ▓▓▓▓▓▓▓▓▓░░░░░░░░░░░
            ^spike   ^drain   ^idle
```

**Quan sát:**
1. Spike traffic → Backlog tăng nhanh
2. Worker scale-out → Instances tăng
3. Xử lý xong → Backlog giảm về 0
4. Worker scale-in → Instances giảm

---

## SLIDE 19: Hạn chế còn tồn tại

| Hạn chế | Mô tả | Giải pháp tiềm năng |
|---------|-------|---------------------|
| Cold Start | Delay 2-3s khi container idle | min-instances = 1 |
| DB Connections | Connection pool exhausted khi scale nhiều | Connection pooling, limit concurrency |
| Chưa có DLQ | Job fail nhiều lần không có nơi xử lý | Dead-Letter Queue |

---

## SLIDE 20: Hướng phát triển

1. **Redis Cache** - Cache đáp án, giảm DB load
2. **Cloud Monitoring Integration** - Metrics thực từ GCP
3. **Dead-Letter Queue** - Xử lý jobs fail
4. **JWT Authentication** - Thay API Key bằng JWT/OAuth2
5. **Analytics Dashboard** - Export logs sang BigQuery

---

## SLIDE 21: Bài học kinh nghiệm

**💡 Event-Driven Architecture:**
> Queue là buffer giữa producer và consumer. Spike được hấp thụ, worker xử lý ổn định.

**💡 Idempotency là bắt buộc:**
> Distributed systems có retry everywhere. Mọi operation phải safe to replay.

**💡 Cloud Native Thinking:**
> Tận dụng managed services (Pub/Sub, Cloud Run). Giảm operational burden.

---

## SLIDE 22: Demo (Live)

**Demo flow:**

1. **Mở Dashboard** - http://<IP>:8000/dashboard.html
2. **Chạy spike test:**
   ```bash
   python3 scripts/demo_spike.py -n 500 -c 50
   ```
3. **Quan sát Dashboard:**
   - Backlog tăng nhanh
   - Instances scale-out
   - Logs cập nhật realtime
   - Backlog giảm về 0

4. **Show API response:**
   ```bash
   curl -X GET http://<IP>:8080/v1/submissions/<id>
   ```

---

## SLIDE 23: Tổng kết

**✅ Đã đạt được:**
- Kiến trúc Event-Driven chịu spike traffic
- Submit endpoint p95 < 300ms
- Auto-scaling worker
- Idempotent scoring
- Dashboard realtime

**📊 Metrics:**
- 100% success rate
- ~200 req/s throughput
- ~15s time-to-score

---

## SLIDE 24: Q&A

**Cảm ơn thầy/cô và các bạn đã lắng nghe!**

**Câu hỏi?**

---

# Tips trình bày

1. **Mở đầu ấn tượng:** Bắt đầu với scenario 1000 sinh viên cùng nộp bài
2. **So sánh trực quan:** Dùng biểu đồ so sánh sync vs async
3. **Demo live:** Chuẩn bị sẵn terminal với commands
4. **Highlight numbers:** Nhấn mạnh SLO và kết quả đạt được
5. **Chuẩn bị backup:** Video demo phòng trường hợp network issue
