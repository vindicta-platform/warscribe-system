import os
import subprocess
from db import Database
from utils import find_audio

class Downloader:
    def __init__(self, output_dir="input", db_path="warscribe.db"):
        self.output_dir = output_dir
        self.db_path = db_path
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_video_id(self, url):
        """Extracts video ID from URL using yt-dlp."""
        cmd = ["yt-dlp", "--print", "id", url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to get video ID: {result.stderr}")
        return result.stdout.strip()

    def _has_ffmpeg(self):
        """Check if ffmpeg is available on the system."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def download_audio(self, url, video_id):
        """Downloads audio. Strategy depends on ffmpeg availability."""
        output_template = os.path.join(self.output_dir, f"{video_id}.%(ext)s")
        
        if self._has_ffmpeg():
            # Ideal: extract audio and convert to wav
            cmd = [
                "yt-dlp",
                "-x",
                "--audio-format", "wav",
                "--audio-quality", "0",
                "-o", output_template,
                url
            ]
        else:
            # No ffmpeg: download best format directly, no post-processing
            # Use broad format selection that works for both VODs and live streams
            cmd = [
                "yt-dlp",
                "-f", "bestaudio/best",  # bestaudio if separate, else best combined
                "-o", output_template,
                url
            ]
        
        print(f"Downloading audio for {video_id}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Primary download failed: {result.stderr.strip()}")
            print("Retrying with fallback format selection...")
            # Ultimate fallback: just download whatever is available
            cmd_fallback = [
                "yt-dlp",
                "-f", "best",
                "-o", output_template,
                url
            ]
            subprocess.run(cmd_fallback, check=True)
        
        return find_audio(self.output_dir, video_id)

    def process(self, url):
        video_id = self.get_video_id(url)
        print(f"Processing {video_id}...")
        
        # Register job
        db = Database(self.db_path)
        db.add_job(video_id, url)
        db.update_job_status(video_id, 'downloading')
        
        try:
            audio_path = self.download_audio(url, video_id)
            if audio_path:
                print(f"Audio saved: {audio_path}")
                db.update_job_status(video_id, 'downloaded')
            else:
                raise FileNotFoundError(f"No audio file found for {video_id}")
        except Exception as e:
            print(f"Download error: {e}")
            # Check if audio already exists from a prior run
            existing = find_audio(self.output_dir, video_id)
            if existing:
                print(f"Found existing audio: {existing}. Continuing...")
                db.update_job_status(video_id, 'downloaded')
            else:
                db.update_job_status(video_id, 'failed')
        
        return video_id

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        d = Downloader("warscribe-system/input")
        d.process(sys.argv[1])
