import os
from faster_whisper import WhisperModel
from db import Database
from utils import find_audio

class Transcriber:
    def __init__(self, model_size="tiny", device="cpu", compute_type="int8", db_path="warscribe.db", input_dir="input"):
        self.db_path = db_path
        self.input_dir = input_dir
        print(f"Loading Whisper model: {model_size} on {device}...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            print(f"Failed to load model on {device}: {e}. Falling back to cpu.")
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def process_job(self, video_id):
        print(f"Processing transcription for job: {video_id}")
        db = Database(self.db_path)
        job_status = self._get_job_status(db, video_id)
        
        if job_status not in ['downloaded', 'transcribing']:
            print(f"Job {video_id} is in status '{job_status}'. Skipping.")
            return

        db.update_job_status(video_id, 'transcribing')
        
        audio_path = find_audio(self.input_dir, video_id)
        if not audio_path:
            print(f"Audio file not found for {video_id} in {self.input_dir}")
            db.update_job_status(video_id, 'failed')
            return
        
        print(f"Using audio file: {audio_path}")

        # Resume from last processed segment if any exist
        existing_segments = db.get_segments(video_id)
        last_end_time = 0.0
        if existing_segments:
            last_end_time = existing_segments[-1]['end_time']
            print(f"Resuming transcription from {last_end_time}s")

        try:
             segments, info = self.model.transcribe(audio_path, beam_size=5)
             
             print("Starting transcription loop...")
             for segment in segments:
                 if segment.end <= last_end_time:
                     continue  # skip already-processed segments

                 seg_id = db.add_segment(
                     video_id, segment.start, segment.end, audio_path
                 )
                 db.update_segment_transcript(seg_id, segment.text)
                 print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

             db.update_job_status(video_id, 'transcribed')
             
        except Exception as e:
            print(f"Transcription failed: {e}")
            db.update_job_status(video_id, 'failed')

    def _get_job_status(self, db, video_id):
        return db.get_job_status(video_id)

if __name__ == "__main__":
    import sys
    t = Transcriber()
    if len(sys.argv) > 1:
        t.process_job(sys.argv[1])
