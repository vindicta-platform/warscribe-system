import chromadb
from chromadb.utils import embedding_functions
from db import Database
import ollama

class QueryEngine:
    def __init__(self, db_path="warscribe.db", chroma_path="warscribe_chroma", llm_model="llama3.2"):
        self.db = Database(db_path)
        self.llm_model = llm_model
        
        try:
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            self.collection = self.chroma_client.get_collection(name="transcripts", embedding_function=self.embedding_fn)
        except Exception as e:
            print(f"Error initializing ChromaDB for QueryEngine: {e}")
            self.collection = None

    def retrieve(self, query, n_results=5, video_id=None):
        if not self.collection:
            return []
            
        where = None
        if video_id:
            where = {"video_id": video_id}
            
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )
        
        # results['documents'] is list of list (batch)
        if results and results['documents']:
            return results['documents'][0]
        return []

    def query(self, question, video_id=None):
        print(f"Retrieving context for: '{question}'...")
        context_docs = self.retrieve(question, n_results=5, video_id=video_id)
        
        if not context_docs:
            return "No relevant context found in the database."
            
        context_text = "\n\n---\n\n".join(context_docs)
        
        prompt = f"""
You are Warscribe, an AI assistant analyzing YouTube video transcripts.
Answer the user's question based ONLY on the following context.
If the answer is not in the context, say "I don't have enough information to answer that."

Context:
{context_text}

Question: {question}

Answer:
"""
        try:
            print("Querying Ollama...")
            response = ollama.chat(model=self.llm_model, messages=[
                {'role': 'user', 'content': prompt},
            ])
            return response['message']['content']
        except Exception as e:
            return f"Error communicating with Ollama: {e}"

if __name__ == "__main__":
    import sys
    engine = QueryEngine()
    
    if len(sys.argv) > 1:
        question = sys.argv[1]
        video_id = sys.argv[2] if len(sys.argv) > 2 else None
        
        print("\n--- Warscribe RAG Query ---")
        answer = engine.query(question, video_id)
        print("\n=== Answer ===\n")
        print(answer)
        print("\n==============")
    else:
        print("Usage: python src/query_engine.py \"Your question here\" [optional_video_id]")
