import base64
import json
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status

from app.db import close_pool, get_conn, init_pool, put_conn

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("score-worker")

app = FastAPI(title="score-worker", version="1.0")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_job(payload: dict) -> dict:
    """
    Parse the payload to extract the job information.
    """
    if "message" in payload and "data" in payload["message"]:
        raw = base64.b64decode(payload["message"]["data"]).decode("utf-8")
        return json.loads(raw)
    if "submissionId" in payload:
        return payload
    raise ValueError("invalid pubsub payload")


def _fetch_questions(conn, exam_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT question_id, correct_choice, points FROM questions WHERE exam_id=%s",
            (exam_id,),
        )
        return cur.fetchall()


@app.on_event("startup")
def _startup():
    init_pool()


@app.on_event("shutdown")
def _shutdown():
    close_pool()


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/v1/score")
def score_job(payload: dict):
    """
    Score a job by:
    - Parsing the payload to extract the job information.
    - Fetching the questions for the exam.
    - Scoring the answers.
    - Updating the submission status.
    """
    submission_id = None
    conn = None
    try:
        # 1. Safe parsing of payload
        try:
            job = _parse_job(payload)
            submission_id = job.get("submissionId")
            exam_id = job.get("examId")
            answers = job.get("answers", [])
        except Exception as exc:
            logger.error("Failed to parse payload: %s", exc)
            return {"ok": True, "error": "invalid_payload"}

        if not submission_id or not exam_id:
            logger.error("Missing submissionId or examId: %s", payload)
            return {"ok": True, "error": "missing_identifiers"}

        # 2. Score logic
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM submissions WHERE submission_id=%s FOR UPDATE",
                    (submission_id,),
                )
                row = cur.fetchone()
                if row is None:
                    logger.warning("Submission not found: %s", submission_id)
                    return {"ok": True}
                if row[0] == "SCORED":
                    return {"ok": True}

                cur.execute(
                    "UPDATE submissions SET status='SCORING' WHERE submission_id=%s",
                    (submission_id,),
                )
                
                # Simulate heavier processing for demo visibility
                time.sleep(0.2)

                questions = _fetch_questions(conn, exam_id)
                if not questions:
                    cur.execute(
                        "UPDATE submissions SET status='FAILED', error_message=%s WHERE submission_id=%s",
                        ("no questions for exam", submission_id),
                    )
                    return {"ok": True}

                question_map = {q[0]: {"correct": q[1], "points": q[2]} for q in questions}
                total = sum(q[2] for q in questions)
                breakdown = []
                score = 0

                for answer in answers:
                    qid = answer.get("questionId")
                    choice = answer.get("choice")
                    if not qid or qid not in question_map:
                        continue
                    correct = question_map[qid]["correct"]
                    points = question_map[qid]["points"]
                    is_correct = choice == correct
                    if is_correct:
                        score += points
                    breakdown.append({
                        "questionId": qid,
                        "choice": choice,
                        "isCorrect": is_correct,
                        "points": points if is_correct else 0,
                    })

                cur.execute("DELETE FROM submission_answers WHERE submission_id=%s", (submission_id,))
                for item in breakdown:
                    cur.execute(
                        """
                        INSERT INTO submission_answers (submission_id, question_id, choice, is_correct, points)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (submission_id, item["questionId"], item["choice"], item["isCorrect"], item["points"]),
                    )

                cur.execute(
                    "UPDATE submissions SET status='SCORED', score=%s, total=%s, scored_at=%s WHERE submission_id=%s",
                    (score, total, _now_iso(), submission_id),
                )
    except Exception as exc:
        logger.exception("Scoring fatal error: %s", exc)
        if submission_id and conn:
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE submissions SET status='FAILED', error_message=%s WHERE submission_id=%s",
                            (str(exc), submission_id),
                        )
            except Exception as db_exc:
                logger.error("Could not mark failed status in DB: %s", db_exc)
    finally:
        if conn:
            put_conn(conn)

    # Always return 200 OK to Pub/Sub
    return {"ok": True}
