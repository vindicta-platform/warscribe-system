import time
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from db import Database
from downloader import Downloader
from transcriber import Transcriber
from chat_parser import ChatParser
from warscribe_llm import WarscribeLLM

class Orchestrator:
    def __init__(self, db_path="warscribe.db"):
        self.db = Database(db_path)
        self.downloader = Downloader("input", db_path=db_path)
        self.transcriber = Transcriber(model_size="tiny", device="cpu", db_path=db_path, input_dir="input")
        self.chat_parser = ChatParser(db_path=db_path)
        self.warscribe_llm = WarscribeLLM(db_path=db_path)
    
    def add_job(self, url):
        # Step 1: Download audio
        print("Starting download phase...")
        video_id = self.downloader.process(url)
        
        # Step 2: Parse live chat (independent of download success)
        print("Starting chat parsing...")
        try:
            self.chat_parser.process_chat(video_id)
        except Exception as e:
            print(f"Chat parsing failed (non-fatal): {e}")
        
        # Step 3: Transcribe audio
        print("Starting transcription...")
        self.transcriber.process_job(video_id)
        
        # Step 4: Extract Warscribe events via LLM
        print("Starting Warscribe extraction...")
        self.warscribe_llm.process_job(video_id)
        
        # Step 5: Generate embeddings for RAG
        print("Generating Embeddings...")
        segments = self.db.get_segments(video_id)
        self.db.add_transcript_embeddings(video_id, segments)
        
        print(f"Job finished for {video_id}")

    def run_loop(self):
        # Placeholder for daemon mode
        while True:
            # check pending jobs
            # check processing jobs
            time.sleep(10)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        orch = Orchestrator()
        orch.add_job(sys.argv[1])
