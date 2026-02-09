"""
Warscribe API — FastAPI gateway for job submission, status, and RAG queries.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from redis import Redis
from rq import Queue

from db import Database
from query_engine import QueryEngine

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
DB_PATH = os.environ.get("DB_PATH", "warscribe.db")

app = FastAPI(title="Warscribe API", version="1.0.0")


def _get_queue():
    conn = Redis.from_url(REDIS_URL)
    return Queue("warscribe", connection=conn)


def _get_db():
    return Database(DB_PATH)


# ── Request / Response Models ──────────────────────────────

class JobRequest(BaseModel):
    url: str

class QueryRequest(BaseModel):
    question: str
    video_id: Optional[str] = None

class IngestRequest(BaseModel):
    file_path: str
    source_id: Optional[str] = None


# ── Job Endpoints ──────────────────────────────────────────

@app.post("/jobs", status_code=201)
def submit_job(req: JobRequest):
    """Submit a YouTube URL for processing."""
    from worker import task_download

    q = _get_queue()
    rq_job = q.enqueue(task_download, req.url, job_timeout="6h")
    return {"message": "Job enqueued", "rq_job_id": rq_job.id, "url": req.url}


@app.get("/jobs")
def list_jobs():
    """List all warscribe processing jobs."""
    db = _get_db()
    return db.list_jobs()


@app.get("/jobs/{video_id}")
def get_job(video_id: str):
    """Get status of a specific job."""
    db = _get_db()
    job = db.get_job(video_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── RAG Query Endpoints ───────────────────────────────────

@app.post("/query")
def rag_query(req: QueryRequest):
    """Query the RAG system with a natural language question."""
    engine = QueryEngine(db_path=DB_PATH)
    answer = engine.query(req.question, video_id=req.video_id)
    return {"question": req.question, "answer": answer, "video_id": req.video_id}


# ── Ingestion Endpoint ────────────────────────────────────

@app.post("/ingest")
def ingest_file(req: IngestRequest):
    """Ingest a text file from the input volume into ChromaDB."""
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")

    from ingest_text import ingest_text_file
    source_id = req.source_id or os.path.basename(req.file_path)
    count = ingest_text_file(req.file_path, source_id=source_id, db_path=DB_PATH)
    return {"message": f"Ingested {count} chunks", "source_id": source_id}


# ── Health ─────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check endpoint."""
    try:
        conn = Redis.from_url(REDIS_URL)
        conn.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {"status": "ok", "redis": redis_ok}
