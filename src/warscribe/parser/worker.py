"""
Warscribe Worker — RQ task functions for the processing pipeline.
Each task completes one phase and enqueues the next.
"""
import os
import sys

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from redis import Redis
from rq import Queue

from db import Database
from downloader import Downloader
from transcriber import Transcriber
from chat_parser import ChatParser
from warscribe_llm import WarscribeLLM

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
DB_PATH = os.environ.get("DB_PATH", "warscribe.db")
INPUT_DIR = os.environ.get("INPUT_DIR", "input")

def _get_queue():
    conn = Redis.from_url(REDIS_URL)
    return Queue("warscribe", connection=conn)


def task_download(url: str):
    """Phase 1: Download audio and parse chat."""
    print(f"[WORKER] Starting download for {url}")
    db = Database(DB_PATH)
    downloader = Downloader(INPUT_DIR, db_path=DB_PATH)
    video_id = downloader.process(url)

    # Chat parsing (non-fatal)
    try:
        parser = ChatParser(db_path=DB_PATH)
        parser.process_chat(video_id)
    except Exception as e:
        print(f"[WORKER] Chat parsing failed (non-fatal): {e}")

    # Enqueue next step
    job_status = db.get_job_status(video_id)
    if job_status != "failed":
        q = _get_queue()
        q.enqueue(task_transcribe, video_id, job_timeout="12h")
        print(f"[WORKER] Enqueued transcription for {video_id}")
    else:
        print(f"[WORKER] Download failed for {video_id}, not enqueuing transcription")

    return video_id


def task_transcribe(video_id: str):
    """Phase 2: Transcribe audio with faster-whisper."""
    print(f"[WORKER] Starting transcription for {video_id}")
    model_size = os.environ.get("WHISPER_MODEL", "tiny")
    device = os.environ.get("WHISPER_DEVICE", "cpu")

    transcriber = Transcriber(
        model_size=model_size,
        device=device,
        db_path=DB_PATH,
        input_dir=INPUT_DIR,
    )
    transcriber.process_job(video_id)

    # Enqueue next step
    db = Database(DB_PATH)
    job_status = db.get_job_status(video_id)
    if job_status == "transcribed":
        q = _get_queue()
        q.enqueue(task_llm_embed, video_id, job_timeout="6h")
        print(f"[WORKER] Enqueued LLM+embed for {video_id}")
    else:
        print(f"[WORKER] Transcription ended with status '{job_status}', not enqueuing LLM")

    return video_id


def task_llm_embed(video_id: str):
    """Phase 3: LLM analysis + embedding generation."""
    print(f"[WORKER] Starting LLM analysis for {video_id}")
    db = Database(DB_PATH)

    # LLM warscribe extraction
    llm = WarscribeLLM(db_path=DB_PATH)
    llm.process_job(video_id)

    # Generate embeddings
    print(f"[WORKER] Generating embeddings for {video_id}")
    segments = db.get_segments(video_id)
    db.add_transcript_embeddings(video_id, segments)

    db.update_job_status(video_id, "completed")
    print(f"[WORKER] Job completed for {video_id}")
    return video_id
