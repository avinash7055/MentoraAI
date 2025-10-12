"""
AI-powered message processing service for handling incoming WhatsApp messages.
Uses transformer models for natural language understanding and intent classification.
"""
import re
import logging
import json
import torch
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline,
    Pipeline
)
from sentence_transformers import SentenceTransformer
import numpy as np

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

class AIIntentClassifier:
    """AI-powered intent classifier using transformer models."""
    
    def __init__(self, model_name: str = "distilbert-base-uncased"):
        """Initialize with a pre-trained model."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing AI Intent Classifier with {model_name} on {self.device}")
        
        try:
            # Initialize tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=len(IntentType),
                id2label={i: intent.value for i, intent in enumerate(IntentType)},
                label2id={intent.value: i for i, intent in enumerate(IntentType)}
            ).to(self.device)
            
            # Initialize zero-shot classification pipeline
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1
            )
            
            # Initialize sentence transformer for semantic similarity
            self.sentence_encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Define intent descriptions for zero-shot classification
            self.intent_descriptions = {
                IntentType.TUTOR: [
                    "User is asking a question or seeking an explanation about a topic",
                    "User wants to understand a concept or get information",
                    "User is curious about a subject and wants to learn more"
                ],
                IntentType.QUIZ: [
                    "User wants to take a test or practice questions",
                    "User is asking for a quiz or assessment",
                    "User wants to test their knowledge on a topic"
                ],
                IntentType.PLAN: [
                    "User wants to create or get a study plan",
                    "User is asking for a schedule or timetable",
                    "User wants to organize their study sessions"
                ],
                IntentType.TRACK: [
                    "User wants to see their progress or statistics",
                    "User is asking about their performance or results",
                    "User wants to track their learning journey"
                ],
                IntentType.GREETING: [
                    "User is greeting or starting a conversation",
                    "User is saying hello or hi",
                    "User is initiating a chat"
                ],
                IntentType.THANKS: [
                    "User is expressing gratitude",
                    "User is saying thank you or thanks",
                    "User is showing appreciation"
                ],
                IntentType.HELP: [
                    "User is asking for help or assistance",
                    "User needs guidance or support",
                    "User is confused and needs clarification"
                ],
                IntentType.FEEDBACK: [
                    "User is providing feedback or suggestions",
                    "User is sharing their opinion or experience",
                    "User is rating or reviewing something"
                ]
            }
            
            # Default responses for simple intents
            self.default_responses = {
                IntentType.GREETING: [
                    "Hello! I'm your AI UPSC Mentor. How can I assist you with your UPSC preparation today? 🚀",
                    "Namaste! I'm here to help you with your UPSC journey. What would you like to work on? 📚",
                    "Hi there! Ready to ace your UPSC preparation? What can I help you with today? 💡"
                ],
                IntentType.THANKS: [
                    "You're welcome! Let me know if you need any more help with your UPSC preparation. 😊",
                    "Happy to help! Keep up the great work with your studies. 🎯",
                    "Anytime! Feel free to ask if you have more questions. Good luck with your preparation! 🌟"
                ],
                IntentType.HELP: [
                    "I can help you with:\n"
                    "📚 Explaining UPSC topics\n"
                    "❓ Answering your questions\n"
                    "📝 Creating quizzes and tests\n"
                    "📅 Generating study plans\n"
                    "📊 Tracking your progress\n\n"
                    "Just ask me anything about UPSC or type what you'd like to do! 😊"
                ]
            }
            
            logger.info("AI Intent Classifier initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Intent Classifier: {str(e)}")
            raise
    
    def detect_intent(self, message: str) -> IntentResult:
        """
        Detect the intent of a message using AI.
        
        Args:
            message: The user's message text
            
        Returns:
            IntentResult containing the detected intent and entities
        """
        if not message or not message.strip():
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={}
            )
        
        try:
            # Prepare candidate labels and their descriptions
            candidate_labels = list(self.intent_descriptions.keys())
            candidate_descriptions = [
                ", ".join(descs) for descs in self.intent_descriptions.values()
            ]
            
            # Get intent classification
            result = self.classifier(
                message,
                candidate_labels=candidate_labels,
                hypothesis_template="This text is about {}.",
                multi_label=False
            )
            
            # Get the most confident intent
            intent = result["labels"][0]
            confidence = result["scores"][0]
            
            # Extract entities based on intent
            entities = self._extract_entities(message, intent)
            
            # Check if we need clarification
            needs_clarification = False
            clarification_prompt = None
            
            if intent == IntentType.QUIZ and not entities.get("topic"):
                needs_clarification = True
                clarification_prompt = "What topic would you like the quiz to be about?"
            elif intent == IntentType.PLAN and not entities.get("subject"):
                needs_clarification = True
                clarification_prompt = "Which subject would you like a study plan for?"
            
            return IntentResult(
                intent=intent,
                confidence=confidence,
                entities=entities,
                needs_clarification=needs_clarification,
                clarification_prompt=clarification_prompt
            )
            
        except Exception as e:
            logger.error(f"Error in intent detection: {str(e)}", exc_info=True)
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={"error": str(e)}
            )
    
    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Extract relevant entities from the message based on intent."""
        entities = {}
        
        # Extract topic/subject entities
        subjects = [
            "history", "geography", "polity", "economics", 
            "science", "environment", "current affairs", "csat",
            "mathematics", "general studies", "essay", "ethics",
            "international relations", "governance", "social justice"
        ]
        
        # Find all mentioned subjects
        mentioned_subjects = [
            subj for subj in subjects 
            if subj in message.lower()
        ]
        
        if mentioned_subjects:
            entities["subjects"] = mentioned_subjects
            entities["primary_subject"] = mentioned_subjects[0]
        
        # Extract specific entity types based on intent
        if intent == IntentType.TUTOR:
            entities["question"] = message.strip()
            
        elif intent == IntentType.QUIZ:
            # Look for difficulty level
            difficulty_keywords = {
                "easy": ["easy", "basic", "simple", "beginner"],
                "medium": ["medium", "moderate", "intermediate"],
                "hard": ["hard", "difficult", "challenging", "advanced"]
            }
            
            for level, keywords in difficulty_keywords.items():
                if any(keyword in message.lower() for keyword in keywords):
                    entities["difficulty"] = level
                    break
            
            # Look for number of questions
            num_match = re.search(r'(\d+)\s*(questions?|qs|mcqs?)', message.lower())
            if num_match:
                entities["num_questions"] = int(num_match.group(1))
            
        elif intent == IntentType.PLAN:
            # Look for duration
            duration_match = re.search(
                r'(\d+)\s*(day|week|month)s?|(daily|weekly|monthly)', 
                message.lower()
            )
            if duration_match:
                if duration_match.group(1) and duration_match.group(2):
                    entities["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}s"
                elif duration_match.group(3):
                    entities["duration"] = duration_match.group(3)
        
        return entities
    
    def get_default_response(self, intent: str) -> Optional[str]:
        """Get a default response for simple intents."""
        if intent in self.default_responses:
            import random
            return random.choice(self.default_responses[intent])
        return None

class AIIntentLoader:
    """Lazy loader for the AI Intent Classifier to handle dependencies."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            try:
                cls._instance = AIIntentClassifier()
            except Exception as e:
                logger.warning(f"Failed to initialize AI Intent Classifier: {str(e)}")
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
    
    def detect_intent(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Detect the intent of a message using AI.
        
        Args:
            message: The user's message
            
        Returns:
            A tuple of (intent_type, intent_data)
        """
        # Use the AI classifier to detect intent
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

# Lazy loader for the AI classifier to handle import dependencies

class AIIntentLoader:
    """Lazy loader for the AI Intent Classifier to handle dependencies."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            try:
                cls._instance = AIIntentClassifier()
            except Exception as e:
                logger.error(f"Failed to initialize AI Intent Classifier: {str(e)}")
                # Fall back to a simple classifier if AI fails
                cls._instance = SimpleIntentClassifier()
        return cls._instance

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
        message = message.strip().lower()
        
        if not message:
            return IntentResult(IntentType.UNKNOWN, 0.0, {})
        
        # Check patterns in order of priority
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(message):
                    return IntentResult(
                        intent=intent,
                        confidence=0.9,  # High confidence for exact matches
                        entities=self._extract_entities(message, intent)
                    )
        
        return IntentResult(IntentType.UNKNOWN, 0.0, {})
    
    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Simple entity extraction."""
        # Simplified entity extraction logic
        return {}
