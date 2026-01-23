INSERT INTO exams (exam_id, title, version)
VALUES ('exam_001', 'Demo exam', 1)
ON CONFLICT (exam_id) DO NOTHING;

INSERT INTO questions (question_id, exam_id, correct_choice, points)
VALUES
  ('q1', 'exam_001', 'B', 1),
  ('q2', 'exam_001', 'A', 1),
  ('q3', 'exam_001', 'C', 1),
  ('q4', 'exam_001', 'D', 1),
  ('q5', 'exam_001', 'A', 1)
ON CONFLICT (question_id) DO NOTHING;
