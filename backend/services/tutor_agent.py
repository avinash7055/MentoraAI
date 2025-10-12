"""
Tutor Agent for handling educational queries and providing detailed responses.
Uses RAG (Retrieval-Augmented Generation) to provide accurate and relevant answers.
"""
import logging
from typing import Dict, Any, Optional

from .base_agent import BaseAgent
from ..config import settings

logger = logging.getLogger(__name__)

class TutorAgent(BaseAgent):
    """Agent responsible for answering educational questions about UPSC topics."""
    
    def __init__(self, rag_service=None):
        """Initialize the TutorAgent with an optional RAG service."""
        super().__init__("TutorAgent")
        self.rag = rag_service
        
        # Initialize RAG service if not provided
        if self.rag is None:
            try:
                from .rag_service import RAGService
                self.rag = RAGService()
            except ImportError as e:
                logger.warning("RAGService not available. Running in limited mode.")
                self.rag = None
    
    async def process_message(self, phone_number: str, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process an educational query and return a detailed response.
        
        Args:
            phone_number: The user's phone number
            message: The user's question or query
            context: Additional context (e.g., conversation history)
            
        Returns:
            A detailed response to the user's query
        """
        try:
            logger.info(f"Processing tutor query from {phone_number}: {message}")
            
            # If RAG service is not available, return a fallback response
            if self.rag is None:
                return (
                    "I'm currently unable to access my knowledge base. "
                    "Please try again later or contact support if the issue persists."
                )
            
            # Get response from RAG service
            response = self.rag.retrieve_and_generate(message)
            
            # Format the response nicely
            formatted_response = self._format_response(response, message)
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error in TutorAgent: {str(e)}", exc_info=True)
            return await self.handle_error(e)
    
    def _format_response(self, response: Any, original_query: str) -> str:
        """Format the RAG response into a user-friendly message.
        
        Args:
            response: The response from RAG service (can be str or dict)
            original_query: The user's original query
            
        Returns:
            Formatted response string
        """
        try:
            # Handle both string and dictionary responses
            if isinstance(response, str):
                answer = response
                sources = []
            elif isinstance(response, dict):
                answer = response.get("answer", "I couldn't find a specific answer to your question.")
                sources = response.get("sources", [])
            else:
                answer = "I received an unexpected response format. Let me try that again."
                sources = []
            
            # Format the response
            formatted = f"🔍 *Question:* {original_query}\n\n"
            formatted += f"📚 *Answer:*\n{answer}\n\n"
            
            if sources and isinstance(sources, list):
                formatted += "📖 *Sources:*\n"
                for i, source in enumerate(sources[:3], 1):  # Limit to top 3 sources
                    if isinstance(source, dict):
                        title = source.get("title", "Untitled")
                        url = source.get("url", "#")
                        formatted += f"{i}. {title}\n   {url}\n"
                    elif isinstance(source, str):
                        formatted += f"{i}. {source}\n"
            
            formatted += "\nNeed more details? Just ask! 😊"
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}", exc_info=True)
            return (
                "I found some information, but had trouble formatting it. "
                "Here's what I have:\n\n" + 
                (response if isinstance(response, str) else 
                 str(response.get("answer", "Sorry, I couldn't process that request.")))
            )
    
    async def generate_answer(self, query: str) -> Dict[str, str]:
        """
        Generate an answer for the given query (synchronous version for backward compatibility).
        
        Args:
            query: The user's question
            
        Returns:
            A dictionary containing the query and answer
        """
        answer = await self.process_message("", query)
        return {"query": query, "answer": answer}
