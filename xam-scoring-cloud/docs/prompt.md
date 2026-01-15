Bạn là senior full-stack + DevOps. Tôi đang làm bài tập lớn Cloud Computing: “Thiết kế và triển khai hệ thống chấm điểm thi trắc nghiệm online có khả năng co giãn trên GCP”.
Hiện tại chỉ yêu cầu: **HOÀN THIỆN TOÀN BỘ CODE LOCAL** (chạy được end-to-end bằng Docker Compose). Sau khi local ổn tôi sẽ deploy lên GCP sau.

# 0) Nguyên tắc làm việc trong Cursor
- Hãy **tạo/ghi đè file trực tiếp trong repo** và mô tả ngắn “đã sửa file X/Y/Z”.
- Không hỏi lại, tự chọn quyết định hợp lý.
- Mọi cấu hình dùng `.env` và `config/env.example`.
- Ưu tiên code gọn, dễ đọc, production-ish (logging, error handling, migrations đơn giản).
- Ngôn ngữ: **NodeJS (TypeScript)**.
- Không dùng thư viện “nặng” nếu không cần.
- Không cần UI frontend, chỉ cần API + worker + scripts test.

# 1) Kiến trúc local cần chạy
- Service A: `exam-api` (HTTP)
  - POST `/v1/exams/:examId/submissions` -> validate -> ghi submission status=RECEIVED -> **enqueue job** -> trả 202 + submissionId
  - GET `/v1/submissions/:submissionId` -> trả status + score
  - GET `/healthz`
  - (Admin) POST `/v1/admin/exams` để seed exam (bảo vệ bằng x-api-key)
- Service B: `score-worker`
  - HTTP endpoint `POST /pubsub/push` (để sau này Pub/Sub push dùng y chang)
  - LOCAL: thay vì Pub/Sub thật, exam-api sẽ gọi HTTP tới worker endpoint để mô phỏng “push delivery” (enqueue = HTTP POST) hoặc dùng một queue in-memory đơn giản.
  - Worker phải:
    - idempotent theo `submissionId`:
      - nếu status == SCORED => return 204/200 ack ngay
    - set status SCORING trong DB, compute score, update status SCORED, ghi breakdown + answers
- Postgres: chạy trong docker
- Schema: dùng đúng file `db/schema.sql` (nếu chưa có thì hãy tạo theo spec).
- Seed: tạo 1 exam mẫu `exam_001` có ~50 câu (có thể generate tự động) để load test.

# 2) Repo structure cần tạo (nếu chưa có)
```

services/
exam-api/
Dockerfile
package.json
tsconfig.json
src/
index.ts
routes.ts
db.ts
validation.ts
types.ts
seed.ts
score-worker/
Dockerfile
package.json
tsconfig.json
src/
index.ts
worker.ts
db.ts
types.ts
db/
schema.sql
seed/
exam_001.json
config/
env.example
docker-compose.yml
README.md
scripts/
smoke-test.sh

```

# 3) DB model & logic (bắt buộc)
- Tables: `exams`, `questions`, `submissions`, `submission_answers` (theo schema SQL).
- Score logic: exact_match, mỗi câu 1 điểm (points theo bảng questions).
- total = sum(points) của exam.
- breakdown lưu theo submission_answers.
- Ensure transaction:
  - worker update status -> insert answers -> update score must be atomic (transaction).
- Handle duplicates:
  - if worker receives same submission twice, do NOT insert duplicates (PK (submission_id, question_id)) và logic skip nếu SCORED.

# 4) Local “queue” mô phỏng Pub/Sub push (để chạy end-to-end)
- Vì local không có Pub/Sub, chọn 1 trong 2:
  A) exam-api sau khi insert submission sẽ HTTP POST tới worker `/pubsub/push` giống format Pub/Sub push (wrapper JSON), worker xử lý.
  B) Dùng Redis queue local (không khuyến nghị nếu không cần).
=> Hãy chọn A (HTTP push) để sau này deploy GCP gần như giữ nguyên.

# 5) Format push message (mô phỏng Pub/Sub push wrapper)
Worker nhận body dạng:
{
  "message": {
    "data": "<base64(JSON_STRING)>",
    "messageId": "local-<uuid>",
    "publishTime": "ISO"
  },
  "subscription": "local-score-jobs-sub"
}
Trong đó JSON_STRING là:
{
  "schemaVersion": 1,
  "jobId": "job_<uuid>",
  "submissionId": "...",
  "examId": "...",
  "userId": "...",
  "answers": [{"questionId":"q1","choice":"B"}, ...],
  "submittedAt": "ISO",
  "traceId": "trace_<uuid>"
}

# 6) Docker Compose
- postgres (port 5432)
- exam-api (port 8080)
- score-worker (port 8081)
- Both services connect to postgres via env.
- On first run: auto-apply schema.sql (có thể dùng init script hoặc entrypoint).
- Healthcheck cho services.

# 7) README & scripts
- README phải có:
  - Cách chạy `docker compose up --build`
  - Cách seed exam (curl admin endpoint hoặc chạy seed.ts)
  - Cách submit bài và poll kết quả (curl example)
- scripts/smoke-test.sh:
  - Wait services
  - Seed exam_001
  - Submit 1 payload ngẫu nhiên
  - Poll GET result đến khi SCORED
  - Print score + head breakdown

# 8) Tiêu chuẩn chất lượng
- TypeScript strict, lint cơ bản (không bắt buộc eslint nếu tốn thời gian)
- Logging: mỗi request log traceId/submissionId
- Error handling: trả JSON rõ
- Không hardcode secrets trong code

# 9) Output yêu cầu từ bạn (Cursor)
- Sau khi sửa file, chỉ trả về:
  1) Danh sách file đã tạo/đã sửa
  2) Cách chạy (3–5 lệnh)
  3) Expected output khi smoke test thành công
Không cần giải thích dài.

Bắt đầu ngay: tạo toàn bộ code theo cấu trúc trên.