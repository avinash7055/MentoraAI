import os
import re
import logging
import chromadb
from chromadb.config import Settings
from typing import Optional
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)

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

    def _clean_response(self, text: str) -> str:
        """Remove any internal thinking tags and clean up the response."""
        if not text:
            return "I couldn't generate a response. Please try again."
            
        # Remove <think>...</think> blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Remove any remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up excessive newlines and whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text).strip()
        return text or "I couldn't generate a proper response. Could you rephrase your question?"

    def retrieve_and_generate(self, query: str) -> str:
        """
        Retrieve relevant context and generate a response using the LLM.
        
        Args:
            query: The user's question
            
        Returns:
            A clean, formatted response based on the retrieved context
        """
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
                
                prompt = f"""You are a helpful UPSC tutor. Use the following study material to answer the question clearly and concisely.
                If the question is not related to the study material, politely explain that you can only answer UPSC-related questions.

                Study Material:
                {context}

                Question: {query}
                
                Answer concisely and directly, without any thinking process or internal dialogue:"""
                
                response = self.llm.generate_text(prompt)
                return self._clean_response(response)
            else:
                return "I couldn't find any relevant information to answer that question in the study materials."
                
        except Exception as e:
            logger.error(f"Error in RAG service: {str(e)}", exc_info=True)
            return "I encountered an error while processing your request. Please try again later."
