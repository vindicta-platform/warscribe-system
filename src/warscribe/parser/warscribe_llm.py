import json
from db import Database
import ollama

class WarscribeLLM:
    def __init__(self, model="llama3", db_path="warscribe.db"):
        self.model = model
        self.db_path = db_path

    def process_job(self, video_id):
        print(f"Processing Warscribe extraction for {video_id}...")
        db = Database(self.db_path)
        
        segments = db.get_segments(video_id)
        
        for segment in segments:
            if segment['transcript'] and not segment['warscribe_json']:
                # Need processing
                print(f"Analyzing segment {segment['id']} ({segment['start_time']}-{segment['end_time']})...")
                
                chat_msgs = db.get_chat_for_segment(video_id, segment['start_time'], segment['end_time'])
                chat_text = "\n".join([f"{m['author']}: {m['message']}" for m in chat_msgs])
                
                prompt = self._create_prompt(segment['transcript'], chat_text)
                
                try:
                    response = ollama.chat(model=self.model, messages=[
                        {'role': 'user', 'content': prompt},
                    ])
                    content = response['message']['content']
                    
                    # Try to extract JSON
                    # Validating JSON is tricky with LLMs, usually need strict mode or parsing.
                    # We'll assume the LLM follows instructions or we wrap in try/catch.
                    
                    warscribe_data = content
                    db.update_segment_warscribe(segment['id'], warscribe_data)
                    
                except Exception as e:
                    print(f"LLM failed for segment {segment['id']}: {e}")

    def _create_prompt(self, transcript, chat_text):
        return f"""
Analyze the following YouTube Live Stream segment (Transcript and Chat) and extract "Warscribe" events.
Output strictly valid JSON.

Transcript:
{transcript}

Chat:
{chat_text}

Extract significant events, sentiment, and topics.
JSON Format:
{{
  "events": [
    {{ "type": "topic_change", "description": "...", "timestamp": ... }},
    {{ "type": "highlight", "description": "...", "timestamp": ... }}
  ],
  "summary": "..."
}}
"""

if __name__ == "__main__":
    import sys
    llm = WarscribeLLM()
    if len(sys.argv) > 1:
        llm.process_job(sys.argv[1])
