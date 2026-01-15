# API Specification (v1)

Base URL: https://<domain>/v1
Auth:
- Option A (recommended): Authorization: Bearer <JWT>
- Option B: x-api-key: <KEY>

## 1) Submit exam
POST /exams/{examId}/submissions

Request body:
{
  "userId": "u_123",
  "answers": [
    {"questionId": "q1", "choice": "B"},
    {"questionId": "q2", "choice": "A"}
  ],
  "clientSubmittedAt": "2026-01-15T10:00:00Z"
}

Response (202 Accepted):
{
  "submissionId": "sub_9f8a...",
  "status": "RECEIVED"
}

Error:
- 400 invalid payload
- 401/403 unauthorized
- 404 exam not found
- 429 rate limited (optional)

## 2) Get submission result
GET /submissions/{submissionId}

Response (200):
{
  "submissionId": "sub_9f8a...",
  "examId": "exam_001",
  "userId": "u_123",
  "status": "RECEIVED|SCORING|SCORED|FAILED",
  "score": 8,
  "total": 10,
  "scoredAt": "2026-01-15T10:00:15Z",
  "breakdown": [
    {"questionId":"q1","isCorrect":true,"points":1},
    {"questionId":"q2","isCorrect":false,"points":0}
  ]
}

## 3) Health checks
GET /healthz
Response: { "ok": true }

## 4) (Optional admin) Create exam (for demo)
POST /admin/exams
Body:
{
  "examId":"exam_001",
  "title":"Demo exam",
  "questions":[
    {"questionId":"q1","correctChoice":"B","points":1},
    {"questionId":"q2","correctChoice":"A","points":1}
  ]
}
Response: { "ok": true }
