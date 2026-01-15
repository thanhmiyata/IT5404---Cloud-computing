# Pub/Sub Contract

Topic: score-jobs

## Message schema (JSON)
{
  "schemaVersion": 1,
  "jobId": "job_<uuid>",
  "submissionId": "sub_<uuid>",
  "examId": "exam_001",
  "userId": "u_123",
  "answers": [
    {"questionId":"q1","choice":"B"},
    {"questionId":"q2","choice":"A"}
  ],
  "submittedAt": "2026-01-15T10:00:00Z",
  "traceId": "trace_<uuid>"
}

## Idempotency rules
- score-worker MUST treat submissionId as idempotent key:
  - If submissions.status == SCORED => ack and skip.
  - If status == SCORING and update_at is recent => skip (optional).
- Pub/Sub retries may deliver duplicates => system must be safe.

## Error handling
- On scoring error: update submissions.status=FAILED + error_message, then ack.
- Optionally publish to dead-letter topic (future extension).
