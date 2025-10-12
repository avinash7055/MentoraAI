"""
Agent Manager for initializing and managing all AI agents.
This module serves as a central point for agent initialization and message routing.
"""
import logging
from typing import Dict, Any, Optional

from .base_agent import BaseAgent
from .tutor_agent import TutorAgent
from .quiz_agent import QuizAgent
from .planner_agent import PlannerAgent
from .tracker_agent import TrackerAgent
from ..config import settings

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages all AI agents and routes messages to the appropriate one."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure only one instance of AgentManager exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize all agents."""
        if self._initialized:
            return
            
        logger.info("Initializing Agent Manager...")
        
        # Initialize all agents
        # Initialize services that can be shared
        from ..services.rag_service import RAGService
        from ..services.llm_service import LLMService
        
        rag_service = RAGService()
        llm_service = LLMService()
        
        self.agents: Dict[str, BaseAgent] = {
            "tutor": TutorAgent(),
            "quiz": QuizAgent(rag_service=rag_service, llm_service=llm_service),
            "planner": PlannerAgent(),
            "tracker": TrackerAgent()
        }
        
        logger.info(f"Initialized {len(self.agents)} agents: {', '.join(self.agents.keys())}")
        self._initialized = True
    
    async def process_message(self, phone_number: str, message: str, intent: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Route the message to the appropriate agent based on intent.
        
        Args:
            phone_number: User's phone number (unique identifier)
            message: The message content
            intent: Detected intent (e.g., 'tutor', 'quiz', 'planner', 'tracker')
            context: Additional context for the conversation
            
        Returns:
            The agent's response as a string
        """
        try:
            logger.info(f"Routing message to {intent} agent")
            
            # Get the appropriate agent
            agent = self.agents.get(intent)
            if not agent:
                logger.warning(f"No agent found for intent: {intent}")
                return self._get_fallback_response(intent)
            
            # Process the message with the agent
            response = await agent.process_message(phone_number, message, context or {})
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return "I encountered an error processing your request. Please try again later."
    
    def _get_fallback_response(self, intent: str) -> str:
        """Get a fallback response when no agent is found for the intent."""
        fallbacks = {
            "tutor": "I'm here to help with your UPSC preparation. What would you like to learn about?",
            "quiz": "I can help you with practice questions. What topic would you like to be quizzed on?",
            "planner": "I can help you create a study plan. What's your target exam date?",
            "tracker": "I can help you track your study progress. What would you like to track?"
        }
        
        return fallbacks.get(intent, "I'm not sure how to help with that. Type 'help' to see what I can do.")

# Create a singleton instance of the AgentManager
agent_manager = AgentManager()
