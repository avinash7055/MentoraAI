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
    
    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        """Initialize with a pre-trained model."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing AI Intent Classifier with {model_name} on {self.device}")
        
        try:
            # Initialize tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name
            ).to(self.device)
            
            # Initialize zero-shot classification pipeline
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                multi_label=False
            )
            
            # Initialize sentence transformer for semantic similarity
            self.sentence_encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Enhanced intent descriptions with more examples and detailed patterns
            self.intent_descriptions = {
                IntentType.TUTOR: "User is asking an educational question or needs explanation about a topic. Examples: 'What is the Indian Constitution?', 'Explain the fundamental rights', 'Tell me about the Mauryan Empire', 'How does the Indian Parliament function?', 'I need help understanding the Preamble', 'Can you explain the role of the President?'",
                IntentType.QUIZ: "User wants to take a quiz or test their knowledge. Examples: 'Give me a quiz on Indian Polity', 'I want to test my knowledge of Modern History', 'Create a 5-question quiz about the Constitution', 'MCQ test on Indian Economy', 'Quiz me on current affairs', 'Give me a practice test for Prelims'",
                IntentType.PLAN: "User wants to create or discuss a study plan. Examples: 'Make me a 30-day study plan', 'I need a weekly schedule for GS Paper 1', 'Help me plan my UPSC preparation', 'Create a 60-day strategy for Mains', 'Daily study plan with 6 hours', 'How should I schedule my revision?'",
                IntentType.TRACK: "User wants to track their progress or see statistics. Examples: 'Show my progress in Polity', 'How am I doing in mock tests?', 'What's my current study time?', 'Track my preparation status', 'My performance in last test', 'How many hours have I studied this week?', 'Show my weak areas'",
                IntentType.GREETING: "User is greeting or starting a conversation. Examples: 'Hi', 'Hello', 'Good morning', 'Namaste', 'Hey there', 'Hi there', 'Good evening', 'Hello bot'",
                IntentType.THANKS: "User is expressing gratitude. Examples: 'Thank you', 'Thanks a lot', 'I appreciate your help', 'Thanks for the information', 'That was helpful, thanks', 'Thank you so much'",
                IntentType.HELP: "User needs help or wants to know what the bot can do. Examples: 'Help', 'What can you do?', 'How does this work?', 'Show me commands', 'What are my options?', 'I need assistance'",
                IntentType.FEEDBACK: "User is providing feedback or reporting an issue. Examples: 'I have a suggestion', 'Report a problem', 'The answer was incorrect', 'I found a mistake', 'This feature is great', 'The explanation was helpful'"
            }
            
            # Intent patterns for quick matching
            self.intent_patterns = {
                IntentType.GREETING: [
                    r'\b(hi|hello|hey|greetings|namaste|hola|good\s*(morning|afternoon|evening))\b',
                ],
                IntentType.HELP: [
                    r'^\s*help\s*$|^\s*what can you do\s*$|^\s*how does this work\s*$',
                ],
                IntentType.THANKS: [
                    r'^\s*(thanks|thank you|appreciate it|grateful|thx|ty)\s*[.!]*\s*$',
                ],
                IntentType.QUIZ: [
                    r'\b(quiz|test|mcq|question|exam|assessment|practice test|mock test|(give|create|make).*\b(quiz|test|mcq))\b',
                ],
                IntentType.PLAN: [
                    r'\b(plan|schedule|timetable|study plan|preparation plan|roadmap|strategy|create.*(plan|schedule)|make.*(plan|schedule))\b',
                ],
                IntentType.TRACK: [
                    r'\b(progress|track|how am i doing|my stats|my performance|my score|how much have i studied|show.*progress|view.*stats)\b',
                ],
                IntentType.TUTOR: [
                    r'\b(explain|teach|what is|who is|define|describe|tell me about|elaborate on|break down|help me understand|i need help with|i want to learn about|i want to know about|can you explain|can you teach me|can you tell me about)\b',
                ]
            }
            
            # Default responses for simple intents
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
                    " Explaining UPSC topics\n"
                    " Answering your questions\n"
                    " Creating quizzes and tests\n"
                    " Generating study plans\n"
                    " Tracking your progress\n\n"
                    "Just ask me anything about UPSC or type what you'd like to do! "
                ]
            }
            
            # Enhanced subject extraction with more patterns
            self.subject_patterns = {
                "history": ["history", "historical", "ancient", "medieval", "modern history", "world history"],
                "geography": ["geography", "geographical", "physical geography", "human geography", "world geography"],
                "polity": ["polity", "constitution", "indian polity", "political science", "governance", "parliament"],
                "economics": ["economics", "economy", "economic development", "indian economy", "macroeconomics"],
                "science": ["science", "general science", "physics", "chemistry", "biology", "science and tech"],
                "environment": ["environment", "ecology", "biodiversity", "environmental studies", "climate change"],
                "current affairs": ["current affairs", "current events", "news", "recent developments"],
                "csat": ["csat", "aptitude", "logical reasoning", "comprehension", "decision making"],
                "ethics": ["ethics", "integrity", "aptitude", "ethics and integrity", "ethics paper 4"],
                "essay": ["essay", "essay writing", "essay paper", "essay preparation"],
                "international relations": ["international relations", "ir", "foreign policy", "global affairs"],
                "governance": ["governance", "social justice", "government policies", "schemes", "welfare"]
            }
            
            # Special topic extraction for polity/governance related topics
            self.topic_patterns = {
                "polity": {
                    "constitution": ["constitution", "fundamental rights", "directive principles", "preamble"],
                    "parliament": ["parliament", "lok sabha", "rajya sabha", "speaker", "chairman"],
                    "president": ["president", "vice president", "election", "powers", "functions"],
                    "judiciary": ["judiciary", "supreme court", "high court", "subordinate courts", "judicial review"],
                    "election": ["election", "electoral process", "voting", "election commission", "model code of conduct"]
                },
                "governance": {
                    "social justice": ["social justice", "equality", "liberty", "fraternity", "human rights"],
                    "government policies": ["government policies", "schemes", "programmes", "initiatives", "budget"],
                    "welfare": ["welfare", "social welfare", "public welfare", "human development", "poverty alleviation"]
                }
            }
            
            logger.info("AI Intent Classifier initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Intent Classifier: {str(e)}")
            raise
    
    def detect_intent(self, message: str) -> IntentResult:
        """
        Detect the intent of a message using AI with improved classification.
        
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
            # Clean and preprocess the message
            message = message.strip().lower()
            
            # First, check for simple patterns that are very clear
            simple_patterns = {
                IntentType.GREETING: [
                    r'^(hi|hello|hey|greetings|namaste|hola|hi there|hey there|good morning|good afternoon|good evening|sup|what\'?s? up|yo)\b',
                ],
                IntentType.THANKS: [
                    r'\b(thank|thanks|thx|ty|appreciate|grateful|cheers)\b',
                ],
                IntentType.HELP: [
                    r'\b(help|support|guide|assist|how (to|do|can)|what (is|are)|how\'?s|what\'?s|where\'?s|when\'?s|who\'?s|why\'?s|whom\'?s|which|explain|tell me( about)?|show me|i need help|can you help|help me|what can you do)\b',
                ]
            }
            
            # Check simple patterns first for quick matching
            for intent, patterns in simple_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, message, re.IGNORECASE):
                        return IntentResult(
                            intent=intent,
                            confidence=0.95,  # High confidence for these clear patterns
                            entities=self._extract_entities(message, intent)
                        )
            
            # Prepare candidate labels and their descriptions for classification
            candidate_labels = list(self.intent_descriptions.keys())
            
            # Get intent classification with improved parameters
            result = self.classifier(
                message,
                candidate_labels=candidate_labels,
                hypothesis_template="This text is about {}.",
                multi_label=False
            )
            
            # Get the most confident intent and its score
            intent = result["labels"][0]
            confidence = result["scores"][0]
            
            # Apply confidence threshold (0.3 is quite low but good for initial filtering)
            if confidence < 0.3:
                # If confidence is low, default to TUTOR for question-like messages
                if any(q_word in message for q_word in ['what', 'when', 'where', 'who', 'why', 'how', '?']):
                    intent = IntentType.TUTOR
                    confidence = 0.8  # Higher confidence for question patterns
            
            # Extract entities based on the detected intent
            entities = self._extract_entities(message, intent)
            
            # Special handling for quiz and plan intents that need clarification
            needs_clarification = False
            clarification_prompt = None
            
            if intent == IntentType.QUIZ and not entities.get("topic"):
                needs_clarification = True
                clarification_prompt = "What topic or chapter would you like to be quizzed on?"
            elif intent == IntentType.PLAN and not entities.get("subject"):
                needs_clarification = True
                clarification_prompt = "Which subject would you like me to create a study plan for?"
            
            return IntentResult(
                intent=intent,
                confidence=confidence,
                entities=entities,
                needs_clarification=needs_clarification,
                clarification_prompt=clarification_prompt
            )
            
        except Exception as e:
            logger.error(f"Error in intent detection: {str(e)}", exc_info=True)
            # Default to TUTOR intent on error if it looks like a question
            is_question = '?' in message or any(q_word in message.split() for q_word in ['what', 'when', 'where', 'who', 'why', 'how'])
            return IntentResult(
                intent=IntentType.TUTOR if is_question else IntentType.UNKNOWN,
                confidence=0.5 if is_question else 0.1,
                entities={"error": str(e) if str(e) else "Unknown error"}
            )
    
    def _extract_entities(self, message: str, intent_type: IntentType) -> Dict[str, Any]:
        """
        Extract relevant entities from the message based on the detected intent.
        """
        entities = {}
        message_lower = message.lower()
        
        # Extract subjects and topics for educational intents
        if intent_type in [IntentType.TUTOR, IntentType.QUIZ, IntentType.PLAN, IntentType.TRACK]:
            # Enhanced subject extraction with more patterns
            subjects = []
            for subject, patterns in self.subject_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        # Special handling for polity/governance variations
                        if subject == 'polity' and 'governance' in message_lower:
                            subjects.append('governance')
                        else:
                            subjects.append(subject)
            
            for word, q_type in question_words.items():
                if message_lower.startswith(word):
                    entities["question_type"] = q_type
                    break
            
        elif intent == IntentType.QUIZ:
            # Look for quiz topics (more comprehensive)
            quiz_topic_patterns = [
                r'(?:quiz|test|mcq|questions?) (?:on|about|for|regarding) (?:the )?(.+?)(?:\?|$|\s|for|on|about)',
                r'(?:give me|i want|need) (?:a )?(?:quiz|test|mcq|questions?) (?:on|about|for)? ?(?:the )?(.+?)(?:\?|$|\s|for|on|about)',
                r'(?:i )?(?:would like|want) (?:to take|to have) (?:a )?(?:quiz|test) (?:on|about) (?:the )?(.+?)(?:\?|$|\s)'
            ]
            
            topic = None
            for pattern in quiz_topic_patterns:
                match = re.search(pattern, message_lower)
                if match and len(match.groups()) > 0:
                    topic = match.group(1).strip()
                    if topic:
                        break
            
            if topic and not mentioned_subjects:
                # If we found a topic but no standard subject, use it as the topic
                entities["topic"] = topic
            
            # Look for difficulty level with more patterns
            difficulty_keywords = {
                "easy": ["easy", "basic", "simple", "beginner", "starter"],
                "medium": ["medium", "moderate", "intermediate", "average"],
                "hard": ["hard", "difficult", "challenging", "advanced", "expert"]
            }
            
            for level, keywords in difficulty_keywords.items():
                if any(f" {keyword} " in f" {message_lower} " for keyword in keywords):
                    entities["difficulty"] = level
                    break
            
            # Look for number of questions with more patterns
            num_match = re.search(r'(\d+)\s*(?:questions?|qs|mcqs?|items?|problems?)', message_lower)
            if num_match:
                entities["num_questions"] = int(num_match.group(1))
            
        elif intent == IntentType.PLAN:
            # Look for study plan duration with more patterns
            duration_match = re.search(
                r'(?:for )?(\d+)\s*(day|week|month|hour)s?|(daily|weekly|monthly)', 
                message_lower
            )
            if duration_match:
                if duration_match.group(1) and duration_match.group(2):
                    entities["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}s"
                elif duration_match.group(3):
                    entities["duration"] = duration_match.group(3)
            
            # Look for study hours per day
            hours_match = re.search(r'(\d+)\s*(?:hours?|hrs?)(?:\s*per\s*day)?', message_lower)
            if hours_match:
                entities["hours_per_day"] = int(hours_match.group(1))
        
        # Additional entity extraction for tracking
        elif intent == IntentType.TRACK:
            if 'progress' in message_lower or 'statistics' in message_lower:
                entities["metric"] = "progress"
            elif 'score' in message_lower or 'marks' in message_lower:
                entities["metric"] = "scores"
            elif 'time' in message_lower or 'hours' in message_lower:
                entities["metric"] = "time_spent"
        
        return entities
    
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
