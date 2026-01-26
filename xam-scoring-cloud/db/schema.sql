CREATE TABLE IF NOT EXISTS exams (
  exam_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  start_at TIMESTAMPTZ,
  end_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
 );

CREATE TABLE IF NOT EXISTS questions (
  question_id TEXT PRIMARY KEY,
  exam_id TEXT NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
  correct_choice TEXT NOT NULL,
  points INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS submissions (
  submission_id TEXT PRIMARY KEY,
  exam_id TEXT NOT NULL REFERENCES exams(exam_id),
  user_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('RECEIVED','SCORING','SCORED','FAILED')),
  score INT,
  total INT,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  scored_at TIMESTAMPTZ,
  error_message TEXT,
  idempotency_key TEXT
);

CREATE INDEX IF NOT EXISTS idx_submissions_exam_received
  ON submissions (exam_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_submissions_user_received
  ON submissions (user_id, received_at DESC);

CREATE TABLE IF NOT EXISTS submission_answers (
  submission_id TEXT NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(question_id),
  choice TEXT NOT NULL,
  is_correct BOOLEAN NOT NULL,
  points INT NOT NULL,
  PRIMARY KEY (submission_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_questions_exam
  ON questions (exam_id);
