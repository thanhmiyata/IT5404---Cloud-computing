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

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="exam-api", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
                cur.execute("SELECT exam_id, start_at, end_at FROM exams WHERE exam_id=%s", (exam_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="exam not found")
                
                start_at, end_at = row[1], row[2]
                now = datetime.now(timezone.utc)
                
                if start_at and now < start_at:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="exam has not started yet")
                if end_at and now > end_at:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="exam has ended")

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


@app.get("/v1/internal/stats")
def get_stats(_: None = Depends(_require_api_key)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Total submissions
            cur.execute("SELECT count(*) FROM submissions")
            total = cur.fetchone()[0]

            # Status breakdown
            cur.execute("SELECT status, count(*) FROM submissions GROUP BY status")
            status_rows = cur.fetchall()
            status_map = {row[0]: row[1] for row in status_rows}

            # Latest logs
            cur.execute(
                """
                SELECT s.submission_id, s.status, s.score, s.total, s.received_at, s.exam_id, e.title, s.user_id
                FROM submissions s
                JOIN exams e ON s.exam_id = e.exam_id
                ORDER BY s.received_at DESC
                LIMIT 20
                """
            )
            log_rows = cur.fetchall()
            logs = [
                {
                    "submissionId": r[0],
                    "status": r[1],
                    "score": r[2],
                    "total": r[3],
                    "at": r[4].isoformat(),
                    "examId": r[5],
                    "examTitle": r[6],
                    "userId": r[7]
                } for r in log_rows
            ]

            # All Exams with timing
            cur.execute("SELECT exam_id, title, start_at, end_at, created_at FROM exams ORDER BY created_at DESC")
            exam_rows = cur.fetchall()
            exams = []
            now = datetime.now(timezone.utc)
            for r in exam_rows:
                status_str = "ACTIVE"
                if r[2] and now < r[2]: status_str = "PENDING"
                if r[3] and now > r[3]: status_str = "CLOSED"
                
                exams.append({
                    "examId": r[0],
                    "title": r[1],
                    "startAt": r[2].isoformat() if r[2] else None,
                    "endAt": r[3].isoformat() if r[3] else None,
                    "createdAt": r[4].isoformat(),
                    "status": status_str
                })

            # Performance Metrics (Throughput and Latency)
            cur.execute(
                """
                SELECT 
                    AVG(EXTRACT(EPOCH FROM (scored_at - received_at))) * 1000 as avg_latency,
                    COUNT(*) FILTER (WHERE scored_at > now() - interval '5 minutes') / 5.0 as rate_per_min
                FROM submissions
                WHERE status = 'SCORED' AND scored_at IS NOT NULL
                """
            )
            perf_row = cur.fetchone()
            avg_latency = round(perf_row[0] or 0)
            processing_rate = round(perf_row[1] or 0, 1)

    finally:
        put_conn(conn)

    # Simulated infrastructure data for Demo
    import random
    backlog = status_map.get("RECEIVED", 0) + status_map.get("SCORING", 0)
    
    # Scale instances based on backlog
    # instances = max(1, min(50, backlog // 5 + 1))
    instances = max(1, min(50, backlog // 2 + 1)) # More sensitive scaling for demo
    
    return {
        "business": {
            "totalSubmissions": total,
            "backlog": backlog,
            "completed": status_map.get("SCORED", 0),
            "failed": status_map.get("FAILED", 0),
            "throughput": processing_rate,
            "latency": avg_latency
        },
        "infrastructure": {
            "instances": instances,
            "cpu": random.randint(30, 85) if backlog > 0 else random.randint(5, 15),
            "memory": random.randint(40, 70),
        },
        "logs": logs,
        "exams": exams
    }


class AdminQuestion(BaseModel):
    questionId: str = Field(..., min_length=1)
    correctChoice: str = Field(..., min_length=1)
    points: int = Field(default=1, ge=0)


class AdminExam(BaseModel):
    examId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    startAt: str | None = None
    endAt: str | None = None
    questions: list[AdminQuestion]


@app.get("/v1/admin/exams/{exam_id}")
def get_exam_detail(exam_id: str, _: None = Depends(_require_api_key)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT exam_id, title, start_at, end_at FROM exams WHERE exam_id=%s", (exam_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="exam not found")
            
            cur.execute("SELECT question_id, correct_choice, points FROM questions WHERE exam_id=%s", (exam_id,))
            q_rows = cur.fetchall()
            questions = [{"questionId": r[0], "correctChoice": r[1], "points": r[2]} for r in q_rows]
            
            return {
                "examId": row[0],
                "title": row[1],
                "startAt": row[2].isoformat() if row[2] else None,
                "endAt": row[3].isoformat() if row[3] else None,
                "questions": questions
            }
    finally:
        put_conn(conn)


@app.post("/v1/admin/exams")
def create_exam(body: AdminExam, _: None = Depends(_require_api_key)):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO exams (exam_id, title, start_at, end_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (exam_id) DO UPDATE SET title=EXCLUDED.title, start_at=EXCLUDED.start_at, end_at=EXCLUDED.end_at
                    """,
                    (body.examId, body.title, body.startAt, body.endAt),
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
