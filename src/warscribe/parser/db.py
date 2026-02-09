import sqlite3
import os
import chromadb
from chromadb.utils import embedding_functions


class Database:
    def __init__(self, db_path="warscribe.db", chroma_path=None):
        self.db_path = db_path
        self._init_db()
        chroma_dir = chroma_path or os.environ.get("CHROMA_PATH", "warscribe_chroma")
        try:
            self.chroma_client = chromadb.PersistentClient(path=chroma_dir)
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            self.collection = self.chroma_client.get_or_create_collection(name="transcripts", embedding_function=self.embedding_fn)
        except Exception as e:
            print(f"Warning: ChromaDB initialization failed: {e}")
            self.chroma_client = None

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Enable WAL mode for concurrent read access
        c.execute("PRAGMA journal_mode=WAL")
        
        # Jobs table: tracks the overall video processing
        c.execute('''CREATE TABLE IF NOT EXISTS jobs (
            video_id TEXT PRIMARY KEY,
            url TEXT,
            status TEXT, -- 'pending', 'downloading', 'processing', 'completed', 'failed'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Segments table: tracks chunks of the video
        c.execute('''CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            segment_index INTEGER,
            start_time REAL,
            end_time REAL,
            audio_path TEXT,
            transcript TEXT,
            chat_data TEXT,
            warscribe_json TEXT,
            status TEXT, -- 'created', 'transcribed', 'analyzed'
            FOREIGN KEY(video_id) REFERENCES jobs(video_id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            timestamp REAL,
            author TEXT,
            message TEXT,
            FOREIGN KEY(video_id) REFERENCES jobs(video_id)
        )''')
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_messages(video_id, timestamp)")
        
        conn.commit()
        conn.close()

    def add_job(self, video_id, url):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO jobs (video_id, url, status) VALUES (?, ?, ?)", 
                  (video_id, url, 'pending'))
        conn.commit()
        conn.close()

    def update_job_status(self, video_id, status):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE video_id = ?", 
                  (status, video_id))
        conn.commit()
        conn.close()

    def add_segment(self, video_id, start_time, end_time, audio_path):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO segments (video_id, start_time, end_time, audio_path, status)
                     VALUES (?, ?, ?, ?, ?)''',
                  (video_id, start_time, end_time, audio_path, 'created'))
        segment_id = c.lastrowid
        conn.commit()
        conn.close()
        return segment_id

    def get_segments(self, video_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM segments WHERE video_id = ? ORDER BY start_time", (video_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_chat_messages(self, messages):
        """messages: list of (video_id, timestamp, author, message)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.executemany("INSERT INTO chat_messages (video_id, timestamp, author, message) VALUES (?, ?, ?, ?)", 
                      messages)
        conn.commit()
        conn.close()
    
    def get_chat_for_segment(self, video_id, start_time, end_time):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM chat_messages WHERE video_id = ? AND timestamp >= ? AND timestamp < ? ORDER BY timestamp", 
                  (video_id, start_time, end_time))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_job_url(self, video_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT url FROM jobs WHERE video_id = ?", (video_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def get_job_status(self, video_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT status FROM jobs WHERE video_id = ?", (video_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    def update_segment_transcript(self, segment_id, transcript):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE segments SET transcript = ?, status = 'transcribed' WHERE id = ?",
                  (transcript, segment_id))
        conn.commit()
        conn.close()

    def update_segment_warscribe(self, segment_id, warscribe_json):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE segments SET warscribe_json = ?, status = 'analyzed' WHERE id = ?",
                  (warscribe_json, segment_id))
        conn.commit()
        conn.close()

    def list_jobs(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_pending_jobs(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM jobs WHERE status = 'pending' ORDER BY created_at ASC")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_job(self, video_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM jobs WHERE video_id = ?", (video_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def _batch_add(self, ids, documents, metadatas, batch_size=1000):
        total = len(ids)
        for i in range(0, total, batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            try:
                self.collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_meta)
                print(f"Added batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({len(batch_ids)} docs)")
            except Exception as e:
                print(f"Error adding batch {i//batch_size + 1}: {e}")

    def add_transcript_embeddings(self, video_id, segments):
        if not self.chroma_client:
            print("ChromaDB not initialized, skipping embeddings.")
            return

        if not segments:
            return

        ids = []
        documents = []
        metadatas = []

        for i, seg in enumerate(segments):
            # seg is expected to be a dict from get_segments
            text = seg.get('transcript', '')
            if text and text.strip():
                ids.append(f"{video_id}_{i}")
                documents.append(text)
                metadatas.append({
                    "video_id": video_id, 
                    "start": seg['start_time'], 
                    "end": seg['end_time'],
                    "source": "transcript"
                })
        
        if documents:
            self._batch_add(ids, documents, metadatas)
            print(f"Finished adding {len(documents)} embeddings to ChromaDB.")

    def add_documents(self, source_id, documents, metadatas):
        """
        Generic method to add documents to ChromaDB.
        source_id: unique identifier for the source (e.g. filename)
        documents: list of text strings
        metadatas: list of dicts. If 'source' key is missing, it will be added.
        """
        if not self.chroma_client:
            print("ChromaDB not initialized.")
            return

        if not documents:
            return

        ids = [f"{source_id}_{i}" for i in range(len(documents))]
        
        # Ensure metadata has 'source'
        final_metadatas = []
        for m in metadatas:
            new_m = m.copy()
            if 'source' not in new_m:
                new_m['source'] = source_id
            final_metadatas.append(new_m)

        self._batch_add(ids, documents, final_metadatas)
        print(f"Finished adding {len(documents)} documents from {source_id}")
