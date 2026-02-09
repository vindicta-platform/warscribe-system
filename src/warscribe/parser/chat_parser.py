from warscribe.core.schema.action import Action, ActionType, ActionResult, BaseAction
from warscribe.core.schema.transcript import GameTranscript, Player
from warscribe.core.schema.unit import UnitReference
from chat_downloader import ChatDownloader
from db import Database
import time

class ChatParser:
    def __init__(self, db_path="warscribe.db"):
        self.db_path = db_path

    def process_chat(self, video_id):
        print(f"Processing chat for {video_id} using ChatDownloader...")
        db = Database(self.db_path)
        url = db.get_job_url(video_id)
        if not url:
            print(f"No URL found for job {video_id}")
            return

        print(f"Fetching chat from {url}...")
        try:
            downloader = ChatDownloader()
            chat = downloader.get_chat(url) # Returns a generator
            
            messages = []
            count = 0
            for message in chat:
                # ChatDownloader returns dicts with various fields.
                # We need: video_id, timestamp (sec), author, message
                
                ts = message.get('time_in_seconds', 0)
                author = message.get('author', {}).get('name', 'Anonymous')
                text = message.get('message', '')
                
                if text:
                    messages.append((video_id, float(ts), author, text))
                    count += 1
                    
                if len(messages) >= 100: # Batch insert
                     db.add_chat_messages(messages)
                     messages = []
                     
            if messages:
                db.add_chat_messages(messages)
                
            print(f"Finished processing chat. Total {count} messages.")
            
        except Exception as e:
            print(f"Error downloading chat: {e}")

if __name__ == "__main__":
    import sys
    # Usage: python src/chat_parser.py <video_id>
    if len(sys.argv) > 1:
        cp = ChatParser()
        cp.process_chat(sys.argv[1])
