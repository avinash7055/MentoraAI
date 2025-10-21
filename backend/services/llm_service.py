import os
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from groq import Groq
from backend.config import settings

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with the Groq API for text generation."""
    
    def __init__(self, model: str = "qwen/qwen3-32b", temperature: float = 0.7):
        """
        Initialize the LLM service with Groq API.
        
        Args:
            model: The model to use for text generation
            temperature: Controls randomness in the response (0.0 to 1.0)
        """
        self.model = model
        self.temperature = temperature
        self.api_key = settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in environment variables")
    
    def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Generate text using the specified Groq model.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            The generated text or error message
        """
        if not self.client:
            return "Error: Groq API key not configured."
            
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return f"Error: {str(e)}"

    def generate_chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """
        Generate text using chat completion format with custom messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            The generated text or error messages
        """
        if not self.client:
            return "Error: Groq API key not configured."
            
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return f"Error: {str(e)}"
