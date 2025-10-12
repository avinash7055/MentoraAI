"""
Base agent class that defines the interface for all agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_name: str):
        """Initialize the agent with a name."""
        self.agent_name = agent_name
        logger.info(f"Initialized {self.agent_name} agent")
    
    @abstractmethod
    async def process_message(self, phone_number: str, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process an incoming message and return a response.
        
        Args:
            phone_number: The user's phone number
            message: The message text
            context: Additional context (e.g., conversation history)
            
        Returns:
            The agent's response as a string
        """
        pass
    
    def get_name(self) -> str:
        """Get the name of the agent."""
        return self.agent_name
    
    async def handle_error(self, error: Exception) -> str:
        """Handle errors that occur during message processing."""
        logger.error(f"Error in {self.agent_name}: {str(error)}", exc_info=True)
        return "I'm sorry, I encountered an error processing your request. Please try again later."
