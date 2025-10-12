import os
import logging
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with the Groq API for text generation."""
    
    def __init__(self, model: str = "qwen/qwen3-32b", temperature: float = 0.7):
        """
        Initialize the LLM service with Groq API.
        
        Args:
            model: The model to use for text generation (default: mixtral-8x7b-32768)
            temperature: Controls randomness in the response (0.0 to 1.0)
        """
        self.model = model
        self.temperature = temperature
        self.api_key = os.getenv("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        
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
        if not self.api_key:
            return "Error: Groq API key not configured."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens
        }
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            
            response_data = response.json()
            
            # Check if the response has the expected structure
            if "choices" not in response_data:
                logger.error(f"Unexpected API response structure: {response_data}")
                return "Error: Unexpected response format from AI service."
            
            if not response_data["choices"] or len(response_data["choices"]) == 0:
                logger.error("No choices in API response")
                return "Error: No response generated."
            
            if "message" not in response_data["choices"][0]:
                logger.error(f"Missing message in choice: {response_data['choices'][0]}")
                return "Error: Invalid response structure."
            
            if "content" not in response_data["choices"][0]["message"]:
                logger.error(f"Missing content in message: {response_data['choices'][0]['message']}")
                return "Error: No content in response."
            
            return response_data["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nResponse: {e.response.text}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return "Error: Failed to parse AI response."
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return "Error: An unexpected error occurred."

    def generate_chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """
        Generate text using chat completion format with custom messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            The generated text or error message
        """
        if not self.api_key:
            return "Error: Groq API key not configured."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            
            response_data = response.json()
            
            # Check if the response has the expected structure
            if "choices" not in response_data:
                logger.error(f"Unexpected API response structure: {response_data}")
                return "Error: Unexpected response format from AI service."
            
            if not response_data["choices"] or len(response_data["choices"]) == 0:
                logger.error("No choices in API response")
                return "Error: No response generated."
            
            if "message" not in response_data["choices"][0]:
                logger.error(f"Missing message in choice: {response_data['choices'][0]}")
                return "Error: Invalid response structure."
            
            if "content" not in response_data["choices"][0]["message"]:
                logger.error(f"Missing content in message: {response_data['choices'][0]['message']}")
                return "Error: No content in response."
            
            return response_data["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nResponse: {e.response.text}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return "Error: Failed to parse AI response."
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return "Error: An unexpected error occurred."
