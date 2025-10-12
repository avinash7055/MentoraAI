import os
import chromadb
from chromadb.config import Settings
from backend.services.llm_service import LLMService

class RAGService:
    def __init__(self):
        # Ensure the data directory exists
        os.makedirs("./data/chroma", exist_ok=True)
        
        # Initialize Chroma client with persistent storage
        self.client = chromadb.PersistentClient(path="./data/chroma")
        
        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name="ncert_corpus",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity for text
        )
        
        self.llm = LLMService()

    def retrieve_and_generate(self, query: str):
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=3
            )
            
            # Extract documents from results
            if 'documents' in results and results['documents'] and len(results['documents']) > 0:
                docs = results['documents'][0]  # Get the first (and only) query result
                context = "\n".join(docs)
                prompt = f"Use the following UPSC study material to answer clearly:\n{context}\nQuestion: {query}\nAnswer:"
                return self.llm.generate_text(prompt)
            else:
                # Fallback if no documents found
                return "I couldn't find any relevant information to answer that question."
                
        except Exception as e:
            print(f"Error in RAG service: {str(e)}")
            return "I encountered an error while processing your request. Please try again later."
