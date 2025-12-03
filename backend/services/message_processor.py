"""
AI-powered message processing service for handling incoming WhatsApp messages.
Uses transformer models for natural language understanding and intent classification.
"""
import re
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class IntentType(str, Enum):
    """Supported intent types with natural language descriptions."""
    TUTOR = "tutor"           # Answer questions and explain concepts
    QUIZ = "quiz"            # Generate or take quizzes
    PLAN = "plan"            # Create study plans
    TRACK = "track"          # Track progress and analytics
    GREETING = "greeting"    # Greetings and small talk
    THANKS = "thanks"        # Expressions of gratitude
    HELP = "help"            # Help requests
    FEEDBACK = "feedback"    # User feedback
    UNKNOWN = "unknown"      # Unclassified intents

@dataclass
class IntentResult:
    """Container for intent classification results."""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None

class GroqIntentClassifier:
    """Intent classifier using Groq LLM for superior reasoning and understanding."""
    
    def __init__(self):
        """Initialize with LLM service."""
        self.llm_service = LLMService()
        logger.info("Initializing Groq Intent Classifier")
        
        self.intent_definitions = {
            IntentType.TUTOR: "User asks educational questions, concepts, definitions, or explanations about UPSC topics (History, Polity, Geography, etc.).",
            IntentType.QUIZ: "User wants to take a quiz, test, MCQ, or practice questions.",
            IntentType.PLAN: "User wants to create, view, or update a study plan/schedule.",
            IntentType.TRACK: "User wants to log study time, view progress, stats, or analytics.",
            IntentType.GREETING: "User says hi, hello, or initiates conversation without specific request.",
            IntentType.THANKS: "User expresses gratitude.",
            IntentType.HELP: "User asks for help or what the bot can do.",
            IntentType.FEEDBACK: "User gives feedback or reports issues."
        }

        self.default_responses = {
            IntentType.GREETING: [
                "Hello! I'm your AI UPSC Mentor. How can I assist you with your UPSC preparation today? ",
                "Namaste! I'm here to help you with your UPSC journey. What would you like to work on? ",
                "Hi there! Ready to ace your UPSC preparation? What can I help you with today? "
            ],
            IntentType.THANKS: [
                "You're welcome! Let me know if you need any more help with your UPSC preparation. ",
                "Happy to help! Keep up the great work with your studies. ",
                "Anytime! Feel free to ask if you have more questions. Good luck with your preparation! "
            ],
            IntentType.HELP: [
                "I can help you with:\n"
                "• 🧠 *AI Tutor*: Ask any UPSC question\n"
                "• 📝 *Quiz Mode*: Type '/quiz history' to practice\n"
                "• 📅 *Study Planner*: Type 'Create a study plan'\n"
                "• 📊 *Progress Tracker*: Type 'Show my progress'\n\n"
                "Just type your question or command to get started!"
            ]
        }

    async def detect_intent(self, message: str) -> IntentResult:
        """
        Detect intent using Groq LLM.
        """
        if not message or not message.strip():
            return IntentResult(IntentType.UNKNOWN, 0.0, {})

        # Check for simple patterns first to save LLM calls
        simple_result = self._check_simple_patterns(message)
        if simple_result:
            return simple_result

        try:
            prompt = f"""Classify this user message into one intent and extract entities.

User Message: "{message}"

Intents:
- tutor: Educational questions/explanations
- quiz: Wants to take a quiz/test
- plan: Create/view study plan
- track: View progress/stats
- greeting: Hi/hello
- thanks: Thank you
- help: Needs help
- feedback: Giving feedback

Return JSON:
{{
    "intent": "intent_name",
    "confidence": 0.95,
    "entities": {{"topic": "...", "subject": "..."}},
    "needs_clarification": false,
    "clarification_prompt": null
}}

Only include entities that are mentioned. If quiz intent but no topic, set needs_clarification=true."""

            response_text = await self.llm_service.get_response(
                prompt, 
                system_prompt="You are a JSON classifier. Return ONLY valid JSON, no explanations or thinking."
            )
            
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response: {response_text[:200]}")
            
            if not response_text or not response_text.strip():
                logger.error("Empty response from LLM")
                return IntentResult(IntentType.UNKNOWN, 0.0, {})
            
            # Parse JSON response
            # Clean up potential markdown code blocks and thinking tags
            clean_json = response_text
            
            # Remove <think> tags (Qwen model uses these for chain-of-thought)
            if "<think>" in clean_json:
                # Extract everything after </think>
                parts = clean_json.split("</think>")
                if len(parts) > 1:
                    clean_json = parts[1]
            
            # Remove markdown code blocks
            clean_json = clean_json.replace("```json", "").replace("```", "").strip()
            
            # Extract JSON object if there's extra text
            # Find the first { and last }
            start_idx = clean_json.find("{")
            end_idx = clean_json.rfind("}")
            
            if start_idx != -1 and end_idx != -1:
                clean_json = clean_json[start_idx:end_idx+1]
            
            # Log cleaned JSON for debugging
            logger.debug(f"Cleaned JSON: {clean_json[:200]}")
            
            result_data = json.loads(clean_json)
            
            return IntentResult(
                intent=result_data.get("intent", IntentType.UNKNOWN),
                confidence=result_data.get("confidence", 0.0),
                entities=result_data.get("entities", {}),
                needs_clarification=result_data.get("needs_clarification", False),
                clarification_prompt=result_data.get("clarification_prompt")
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.error(f"Response was: {response_text if 'response_text' in locals() else 'No response'}")
            return IntentResult(IntentType.UNKNOWN, 0.0, {})
        except Exception as e:
            logger.error(f"Groq intent detection failed: {str(e)}", exc_info=True)
            return IntentResult(IntentType.UNKNOWN, 0.0, {})

    def _check_simple_patterns(self, message: str) -> Optional[IntentResult]:
        """Quick regex check for obvious intents."""
        message_lower = message.lower()
        
        patterns = {
            IntentType.GREETING: [r'\b(hi|hello|hey|namaste)\b'],
            IntentType.THANKS: [r'\b(thanks|thank you)\b'],
            IntentType.HELP: [r'\b(help|commands|menu)\b']
        }

        for intent, regex_list in patterns.items():
            for pattern in regex_list:
                if re.search(pattern, message_lower):
                    return IntentResult(intent, 1.0, {})
        return None

    def get_default_response(self, intent: str) -> Optional[str]:
        """Get a default response for simple intents."""
        if intent in self.default_responses:
            import random
            return random.choice(self.default_responses[intent])
        return None
    
    def get_default_response(self, intent: str) -> Optional[str]:
        """Get a default response for simple intents."""
        if intent in self.default_responses:
            import random
            return random.choice(self.default_responses[intent])
        return None

class SimpleIntentClassifier:
    """Simple fallback intent classifier when AI is not available."""
    
    def __init__(self):
        logger.warning("Using SimpleIntentClassifier as fallback")
        self.patterns = {
            IntentType.TUTOR: [
                r"(what|when|where|who|why|how|explain|tell me about|what is|what are|can you help|help me with|i need help with)",
                r"(define|describe|elaborate|details? about|information about|know about|learn about|teach me about)",
            ],
            IntentType.QUIZ: [
                r"(test me|quiz me|give me a quiz|take a test|practi[cs]e questions|mcq|multiple choice|quiz on|test on|questions on)",
                r"(i want to practice|i need practice|i want to test myself|i want to take a quiz)",
            ],
            IntentType.PLAN: [
                r"(study plan|study schedule|timetable|study routine|daily plan|weekly plan|monthly plan|plan my studies)",
                r"(create a plan|make a schedule|organize my study|how should i plan|i need a study plan)",
            ],
            IntentType.TRACK: [
                r"(my progress|my performance|my stats|my statistics|track my progress|how am i doing|my results|my scores)",
                r"(show me my progress|view my performance|check my stats|see my results|how much have i completed)",
            ],
            IntentType.GREETING: [
                r"^(hi|hello|hey|greetings|namaste|hola|hi there|hey there|good morning|good afternoon|good evening)",
                r"(howdy|what's up|yo|sup|hi bot|hello bot|hey bot|hi assistant|hello assistant|hey assistant)",
            ],
            IntentType.THANKS: [
                r"(thank you|thanks|thanks a lot|thank you so much|appreciate it|grateful|thanks for your help|thank you for helping)",
                r"(thanks a bunch|many thanks|thanks a ton|thank you very much|i appreciate it|you're the best|you rock)",
            ],
            IntentType.HELP: [
                r"(help|i need help|can you help|assist me|support|i need support|guide me|what can you do|how does this work)",
                r"(i'm stuck|i need guidance|can you assist|help me out|what should i do|i don't understand|how to use)",
            ],
            IntentType.FEEDBACK: [
                r"(feedback|suggestion|i have a suggestion|i want to give feedback|i want to suggest|i have an idea|report an issue)",
                r"(this is not working|i don't like this|this is great|i love this|improvement|how can i improve|rate this)",
            ]
        }
        self.compiled_patterns = {
            intent: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for intent, patterns in self.patterns.items()
        }
    
    def detect_intent(self, message: str) -> IntentResult:
        """Simple pattern-based intent detection."""
        if not message or not message.strip():
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={}
            )
            
        message_lower = message.lower()
        
        # Check each intent's patterns
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(message_lower):
                    entities = self._extract_entities(message_lower, intent)
                    return IntentResult(
                        intent=intent,
                        confidence=0.8,  # Lower confidence for pattern matching
                        entities=entities
                    )
        
        # Default to TUTOR if no pattern matches but looks like a question
        if '?' in message or any(word in message_lower for word in ['what', 'when', 'where', 'who', 'why', 'how']):
            return IntentResult(
                intent=IntentType.TUTOR,
                confidence=0.6,
                entities={"question": message.strip()}
            )
            
        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            entities={}
        )
    
    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Simple entity extraction."""
        entities = {}
        
        # Extract potential topics/subjects
        subjects = [
            "history", "geography", "polity", "economics", 
            "science", "environment", "current affairs", "csat",
            "mathematics", "general studies", "essay", "ethics",
            "international relations", "governance", "social justice"
        ]
        
        mentioned_subjects = [
            subj for subj in subjects 
            if subj in message.lower()
        ]
        
        if mentioned_subjects:
            entities["subjects"] = mentioned_subjects
            entities["primary_subject"] = mentioned_subjects[0]
        
        return entities

class AIIntentLoader:
    """Lazy loader for the Groq Intent Classifier to handle dependencies."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            try:
                cls._instance = GroqIntentClassifier()
            except Exception as e:
                logger.warning(f"Failed to initialize Groq Intent Classifier: {str(e)}")
                logger.warning("Falling back to SimpleIntentClassifier")
                cls._instance = SimpleIntentClassifier()
        return cls._instance

# Create a singleton instance of the AI Intent Classifier
ai_classifier = AIIntentLoader()

class MessageProcessor:
    """Processes and routes incoming messages to the appropriate handler."""
    
    def __init__(self):
        self.classifier = ai_classifier
        logger.info("Message Processor initialized with AI Intent Classifier")
    
    async def detect_intent(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Detect the intent of a message using AI.
        
        Args:
            message: The user's message
            
        Returns:
            A tuple of (intent_type, intent_data)
        """
        # Use the AI classifier to detect intent
        # Check if it's the async Groq classifier or sync Simple classifier
        if hasattr(self.classifier, 'detect_intent') and asyncio.iscoroutinefunction(self.classifier.detect_intent):
            result = await self.classifier.detect_intent(message)
        else:
            result = self.classifier.detect_intent(message)
        
        # If we need clarification, return that instead
        if result.needs_clarification and result.clarification_prompt:
            return "clarification_needed", {"prompt": result.clarification_prompt}
        
        # Convert to the expected return format
        return result.intent, {
            **result.entities,
            "_confidence": result.confidence,
            "_raw_intent": result.intent
        }
    
    def get_default_response(self, intent: str) -> Optional[str]:
        """
        Get a default response for simple intents.
        
        Args:
            intent: The detected intent
            
        Returns:
            A default response message, or None if no default exists
        """
        return self.classifier.get_default_response(intent)
# Create a singleton instance of the MessageProcessor
message_processor = MessageProcessor()

# Create a singleton instance of the MessageProcessor
message_processor = MessageProcessor()
