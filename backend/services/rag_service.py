import chromadb
from chromadb.config import Settings
from services.llm_service import LLMService

class RAGService:
    def __init__(self):
        self.client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./data/chroma"))
        self.collection = self.client.get_or_create_collection("ncert_corpus")
        self.llm = LLMService()

    def retrieve_and_generate(self, query: str):
        results = self.collection.query(query_texts=[query], n_results=3)
        docs = [r for r in results['documents'][0]]
        context = "\n".join(docs)
        prompt = f"Use the following UPSC study material to answer clearly:\n{context}\nQuestion: {query}\nAnswer:"
        return self.llm.generate_text(prompt)
