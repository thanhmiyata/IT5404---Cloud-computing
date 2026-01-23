import json
import logging
import os
import uuid
from datetime import datetime, timezone

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, status
from google.cloud import pubsub_v1
from pydantic import BaseModel, Field

from app.db import close_pool, get_conn, init_pool, put_conn

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("exam-api")

API_KEY = os.getenv("API_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "score-jobs")
PUBSUB_DISABLED = os.getenv("PUBSUB_DISABLED", "false").lower() == "true"
SCORE_WORKER_URL = os.getenv("SCORE_WORKER_URL")

app = FastAPI(title="exam-api", version="1.0")


class AnswerItem(BaseModel):
    questionId: str = Field(..., min_length=1)
    choice: str = Field(..., min_length=1)


class SubmitRequest(BaseModel):
    userId: str = Field(..., min_length=1)
    answers: list[AnswerItem]
    clientSubmittedAt: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


def _publish_job(payload: dict) -> None:
    if PUBSUB_DISABLED:
        if SCORE_WORKER_URL:
            try:
                requests.post(SCORE_WORKER_URL, json=payload, timeout=5)
                logger.info("direct dispatch to worker: %s", payload["submissionId"])
            except requests.RequestException as exc:
                raise RuntimeError(f"direct dispatch failed: {exc}") from exc
        else:
            logger.info("PUBSUB_DISABLED=true, skip publish: %s", payload["submissionId"])
        return
    if not PROJECT_ID:
        raise RuntimeError("GCP_PROJECT_ID is required to publish")
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
    data = json.dumps(payload).encode("utf-8")
    future = publisher.publish(topic_path, data=data)
    future.result(timeout=10)


def _get_exam_questions(conn, exam_id: str):
    with conn.cursor() as cur:
        cur.execute("SELECT question_id, points FROM questions WHERE exam_id=%s", (exam_id,))
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


@app.post("/v1/exams/{exam_id}/submissions", status_code=status.HTTP_202_ACCEPTED)
def submit_exam(exam_id: str, body: SubmitRequest, _: None = Depends(_require_api_key)):
    submission_id = f"sub_{uuid.uuid4().hex}"
    trace_id = f"trace_{uuid.uuid4().hex}"

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT exam_id FROM exams WHERE exam_id=%s", (exam_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="exam not found")

                questions = _get_exam_questions(conn, exam_id)
                total = sum(row[1] for row in questions) if questions else 0
                cur.execute(
                    """
                    INSERT INTO submissions (submission_id, exam_id, user_id, status, total)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (submission_id, exam_id, body.userId, "RECEIVED", total),
                )

        message = {
            "schemaVersion": 1,
            "jobId": f"job_{uuid.uuid4().hex}",
            "submissionId": submission_id,
            "examId": exam_id,
            "userId": body.userId,
            "answers": [a.model_dump() for a in body.answers],
            "submittedAt": body.clientSubmittedAt or _now_iso(),
            "traceId": trace_id,
        }
        _publish_job(message)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("submit failed: %s", exc)
        conn.rollback()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE submissions SET status='FAILED', error_message=%s WHERE submission_id=%s",
                    (str(exc), submission_id),
                )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="submit failed")
    finally:
        put_conn(conn)

    return {"submissionId": submission_id, "status": "RECEIVED"}


@app.get("/v1/submissions/{submission_id}")
def get_submission(submission_id: str, _: None = Depends(_require_api_key)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT submission_id, exam_id, user_id, status, score, total, scored_at
                FROM submissions
                WHERE submission_id=%s
                """,
                (submission_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="submission not found")

            cur.execute(
                """
                SELECT question_id, is_correct, points
                FROM submission_answers
                WHERE submission_id=%s
                ORDER BY question_id
                """,
                (submission_id,),
            )
            breakdown_rows = cur.fetchall()
    finally:
        put_conn(conn)

    breakdown = [
        {"questionId": r[0], "isCorrect": r[1], "points": r[2]} for r in breakdown_rows
    ]
    return {
        "submissionId": row[0],
        "examId": row[1],
        "userId": row[2],
        "status": row[3],
        "score": row[4],
        "total": row[5],
        "scoredAt": row[6].isoformat() if row[6] else None,
        "breakdown": breakdown,
    }


class AdminQuestion(BaseModel):
    questionId: str = Field(..., min_length=1)
    correctChoice: str = Field(..., min_length=1)
    points: int = Field(default=1, ge=0)


class AdminExam(BaseModel):
    examId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    questions: list[AdminQuestion]


@app.post("/v1/admin/exams")
def create_exam(body: AdminExam, _: None = Depends(_require_api_key)):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO exams (exam_id, title)
                    VALUES (%s, %s)
                    ON CONFLICT (exam_id) DO UPDATE SET title=EXCLUDED.title
                    """,
                    (body.examId, body.title),
                )
                cur.execute("DELETE FROM questions WHERE exam_id=%s", (body.examId,))
                for q in body.questions:
                    cur.execute(
                        """
                        INSERT INTO questions (question_id, exam_id, correct_choice, points)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (q.questionId, body.examId, q.correctChoice, q.points),
                    )
    finally:
        put_conn(conn)

    return {"ok": True}
