import sys
import os
import argparse
from db import Database

def ingest_text_file(file_path, source_id=None, db_path="warscribe.db"):
    """Ingest a text file into ChromaDB. Returns number of chunks ingested."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
    
    if not chunks:
        print("No content found in file.")
        return 0

    db = Database(db_path)
    filename = os.path.basename(file_path)
    sid = source_id or filename.replace(" ", "_")

    print(f"Ingesting {len(chunks)} chunks from {filename}...")
    
    documents = chunks
    metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]
    
    db.add_documents(sid, documents, metadatas)
    print("Done.")
    return len(chunks)


def ingest_file(file_path):
    """CLI wrapper for backward compatibility."""
    ingest_text_file(file_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a text file into Warscribe RAG")
    parser.add_argument("file", help="Path to text file")
    args = parser.parse_args()
    
    ingest_file(args.file)
