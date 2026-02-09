import sys
from db import Database

def retry_embeddings(video_id):
    db = Database()
    segments = db.get_segments(video_id)
    
    if not segments:
        print(f"No segments found for {video_id}. Transcription might have failed.")
        return

    print(f"Found {len(segments)} segments. Generating embeddings...")
    db.add_transcript_embeddings(video_id, segments)
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        retry_embeddings(sys.argv[1])
    else:
        print("Usage: python src/retry_embeddings.py <video_id>")
