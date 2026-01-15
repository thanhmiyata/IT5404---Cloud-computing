# Data Model (PostgreSQL)

## Entities
1) exams
- exam_id (PK)
- title
- version
- created_at

2) questions
- question_id (PK)
- exam_id (FK)
- correct_choice
- points

3) submissions
- submission_id (PK)
- exam_id (FK)
- user_id
- status: RECEIVED/SCORING/SCORED/FAILED
- score
- total
- received_at
- scored_at
- error_message (nullable)
- idempotency_key (optional)

4) submission_answers (optional but good for “hệ thống thật”)
- submission_id (FK)
- question_id (FK)
- choice
- is_correct
- points
- PRIMARY KEY (submission_id, question_id)

## Indexes
- submissions(exam_id, received_at)
- submissions(user_id, received_at)
- questions(exam_id)