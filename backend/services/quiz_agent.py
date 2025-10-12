"""
Enhanced Quiz Agent for generating and evaluating UPSC-style quizzes.
Handles quiz generation, question presentation, and answer evaluation with session management.
"""
import json
import logging
import re
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .base_agent import BaseAgent
from .rag_service import RAGService
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class QuizAgent(BaseAgent):
    """
    Enhanced Quiz Agent that handles quiz generation, delivery, and evaluation
    with session management and progress tracking.
    """

    def __init__(self, rag_service: Optional[RAGService] = None, llm_service: Optional[LLMService] = None):
        """Initialize the QuizAgent with optional RAG and LLM services."""
        super().__init__("QuizAgent")
        self.rag = rag_service or RAGService()
        self.llm = llm_service or LLMService()
        self.active_quizzes: Dict[str, Dict] = {}  # user_id -> quiz_data
        self.user_progress: Dict[str, Dict] = {}  # user_id -> progress_data
        
        # Quiz configuration
        self.difficulty_levels = {
            "easy": {"num_questions": 5, "context_size": 2},
            "medium": {"num_questions": 7, "context_size": 3},
            "hard": {"num_questions": 10, "context_size": 5}
        }
        
        self.default_quiz_config = {
            "num_questions": 5,
            "difficulty": "medium",
            "topics": ["general"]
        }

    async def process_message(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a quiz-related message and return an appropriate response.
        
        Args:
            user_id: Unique identifier for the user
            message: The user's message (quiz request or answer)
            context: Additional context (e.g., current quiz state)
            
        Returns:
            A response message with quiz questions or feedback
        """
        try:
            # Check if this is an answer to an active quiz
            if user_id in self.active_quizzes:
                return await self._handle_quiz_response(user_id, message)
            
            # Otherwise, start a new quiz
            return await self.start_quiz_session(user_id, message)
            
        except Exception as e:
            logger.error(f"Error in QuizAgent: {str(e)}", exc_info=True)
            return "I encountered an error processing your request. Please try again."

    async def start_quiz_session(self, user_id: str, topic: str, difficulty: str = "medium") -> str:
        """Start a new quiz session for the user."""
        try:
            # Generate quiz questions
            questions = await self.generate_quiz(
                topic=topic,
                num_questions=self.difficulty_levels.get(difficulty, {}).get("num_questions", 5),
                difficulty=difficulty
            )
            
            if not questions:
                return "I couldn't generate any questions on that topic. Please try another topic or ask me something else!"
            
            # Store the quiz state
            self.active_quizzes[user_id] = {
                "questions": questions,
                "current_question": 0,
                "score": 0,
                "responses": [],
                "topic": topic,
                "difficulty": difficulty,
                "start_time": datetime.utcnow().isoformat()
            }
            
            # Return the first question
            return self._format_question(user_id)
            
        except Exception as e:
            logger.error(f"Error starting quiz session: {str(e)}", exc_info=True)
            return "I had trouble creating your quiz. Please try again with a different topic."

    async def generate_quiz(self, topic: str, num_questions: int = 5, difficulty: str = "medium") -> List[Dict]:
        """
        Generate UPSC-style MCQs for a given topic using RAG context.
        
        Args:
            topic: The topic for the quiz
            num_questions: Number of questions to generate (1-10)
            difficulty: Difficulty level (easy, medium, hard)
            
        Returns:
            List of question dictionaries
        """
        try:
            # Get relevant context using RAG
            context_size = self.difficulty_levels.get(difficulty, {}).get("context_size", 3)
            docs = self.rag.collection.query(
                query_texts=[topic],
                n_results=context_size
            )
            
            context = "\n\n".join(sum(docs["documents"], [])) if docs and "documents" in docs else ""
            
            system_prompt = """You are an expert UPSC exam question setter. Generate ONLY a valid JSON array of multiple-choice questions. 

CRITICAL REQUIREMENTS:
1. Return ONLY a JSON array - no explanations, no markdown, no other text
2. Each question must have exactly 4 options labeled A, B, C, D
3. Answer must be exactly one letter: A, B, C, or D
4. Use this EXACT format for each question:
{
  "question": "Your question here?",
  "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
  "answer": "C"
}

Example:
[
  {
    "question": "What is the capital of India?",
    "options": ["A. Mumbai", "B. Kolkata", "C. New Delhi", "D. Chennai"],
    "answer": "C"
  }
]"""
            
            user_prompt = f"""Create exactly {num_questions} UPSC-style multiple-choice questions based on this context:

{context}

Return ONLY the JSON array. No explanations, no markdown, no other text."""
            
            # Use chat completion format for better control
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Get the raw response
            if hasattr(self.llm, 'generate_chat'):
                result = self.llm.generate_chat(messages)
            else:
                result = self.llm.generate_text("""
                Generate a JSON array of quiz questions based on the context. 
                Return ONLY the JSON array with no other text or formatting.
                Context: """ + context)
            
            try:
                # Clean the response
                result = result.strip()
                logger.debug(f"Raw LLM response: {result[:500]}...")
                
                # Check for error responses
                if result.startswith("Error:"):
                    logger.error(f"LLM returned error: {result}")
                    raise ValueError(f"LLM service error: {result}")
                
                # Remove any thinking/explanation blocks
                if '<think>' in result.lower() and '</think>' in result.lower():
                    result = re.sub(r'(?is)<think>.*?<\/think>', '', result)
                
                # Handle markdown code blocks
                if '```json' in result:
                    result = result.split('```json', 1)[1].split('```', 1)[0].strip()
                elif '```' in result:
                    result = result.split('```', 1)[1].rsplit('```', 1)[0].strip()
                
                # Find JSON array boundaries - be more lenient with whitespace
                result = re.sub(r'^[^\[]*', '', result)  # Remove anything before first [
                result = re.sub(r'[^\]]*$', '', result)  # Remove anything after last ]
                result = result.strip()
                
                if not result or result[0] != '[' or result[-1] != ']':
                    logger.error(f"No valid JSON array found. First 200 chars: {result[:200]}")
                    # Try to extract JSON from the response
                    json_match = re.search(r'\[.*\]', result, re.DOTALL)
                    if json_match:
                        result = json_match.group(0)
                        logger.info(f"Extracted JSON from response: {result[:100]}...")
                    else:
                        raise ValueError("No valid JSON array found in response")
                
                # Try to parse the JSON
                try:
                    questions = json.loads(result)
                except json.JSONDecodeError as e:
                    # Try to fix common JSON issues
                    logger.warning(f"Initial JSON parse failed, attempting to clean: {str(e)}")
                    
                    # Fix common issues
                    fixed = result
                    # Remove trailing commas
                    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
                    # Fix empty values
                    fixed = re.sub(r'([\{\[,])\s*([\}\],])', r'\1null\2', fixed)
                    # Fix unescaped quotes in strings
                    fixed = re.sub(r'(["\'])([^"\']*)\1', r'"\2"', fixed)
                    
                    # Try parsing again
                    try:
                        questions = json.loads(fixed)
                    except json.JSONDecodeError as e2:
                        logger.error(f"Failed to parse JSON after cleaning: {str(e2)}")
                        logger.debug(f"Problematic JSON: {fixed[:500]}...")
                        # Return a fallback question
                        return [{
                            "question": "Sorry, I had trouble generating quiz questions. Please try again with a different topic.",
                            "options": ["A. OK", "B. Try again", "C. Different topic", "D. Skip"],
                            "answer": "A"
                        }]
                
                # Validate the structure
                if not isinstance(questions, list):
                    logger.error(f"Expected JSON array, got {type(questions)}")
                    raise ValueError("Expected a JSON array of questions")
                
                validated_questions = []
                for i, q in enumerate(questions):
                    try:
                        if not isinstance(q, dict):
                            logger.warning(f"Question {i} is not a dictionary: {q}")
                            continue
                            
                        if not all(k in q for k in ["question", "options", "answer"]):
                            logger.warning(f"Question {i} missing required fields: {q}")
                            continue
                            
                        # Ensure options is a list of 4 strings
                        if not isinstance(q.get("options"), list) or len(q["options"]) != 4:
                            logger.warning(f"Question {i} must have exactly 4 options: {q}")
                            continue
                            
                        # Ensure answer is one of A, B, C, D
                        answer = str(q.get("answer", "")).strip().upper()
                        if answer not in ["A", "B", "C", "D"]:
                            logger.warning(f"Question {i} has invalid answer: {q.get('answer')}")
                            continue
                            
                        # Clean up the question and options
                        clean_q = {
                            "question": str(q["question"]).strip(),
                            "options": [str(opt).strip() for opt in q["options"]],
                            "answer": answer
                        }
                        
                        validated_questions.append(clean_q)
                        
                        # Stop if we have enough questions
                        if len(validated_questions) >= num_questions:
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error validating question {i}: {str(e)}")
                        continue
                
                if not validated_questions:
                    logger.warning("No valid questions could be generated from the response")
                    # Return a fallback question
                    return [{
                        "question": "I couldn't generate valid quiz questions for this topic. Please try a different topic.",
                        "options": ["A. OK", "B. Try again", "C. Different topic", "D. Skip"],
                        "answer": "A"
                    }]
                    
                return validated_questions
                
            except Exception as e:
                logger.error(f"Error generating quiz: {str(e)}\nResponse: {result[:500]}", exc_info=True)
                return [{
                    "question": "We encountered an issue generating your quiz. Please try again with a different topic.",
                    "options": ["OK"],
                    "answer": "A"
                }]
                
        except Exception as e:
            logger.error(f"Error generating quiz: {str(e)}", exc_info=True)
            return [{
                "question": "An error occurred while generating the quiz. Please try again.",
                "options": ["OK"],
                "answer": "A"
            }]

    async def process_answer(self, user_id: str, answer: str) -> str:
        """
        Process a user's answer to the current quiz question.
        
        Args:
            user_id: The user's unique identifier
            answer: The user's answer (A, B, C, or D)
            
        Returns:
            Feedback on the answer and the next question or quiz results
        """
        if user_id not in self.active_quizzes:
            return "You don't have an active quiz. Start a new one with '/quiz <topic>'"
            
        quiz = self.active_quizzes[user_id]
        current_q = quiz["current_question"]
        questions = quiz["questions"]
        
        if current_q >= len(questions):
            return await self._finalize_quiz(user_id)
            
        # Process the answer
        question = questions[current_q]
        is_correct = answer.strip().upper() == question["answer"].strip().upper()
        
        # Update quiz state
        if is_correct:
            quiz["score"] += 1
        quiz["responses"].append({
            "question_idx": current_q,
            "answer": answer,
            "is_correct": is_correct,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Move to next question
        quiz["current_question"] += 1
        
        # Provide feedback and next question or results
        feedback = f"{'✅ Correct!' if is_correct else '❌ Incorrect! The correct answer was ' + question['answer']}\n\n"
        
        if quiz["current_question"] < len(questions):
            return feedback + self._format_question(user_id)
        else:
            return await self._finalize_quiz(user_id, feedback)
    
    async def _handle_quiz_response(self, user_id: str, message: str) -> str:
        """Handle user response during an active quiz session."""
        # Check for special commands
        message = message.strip().lower()
        
        if message in ["hint", "/hint"]:
            return self._get_hint(user_id)
        elif message in ["skip", "/skip"]:
            return await self._skip_question(user_id)
        elif message in ["quit", "exit", "/quit", "/exit"]:
            return await self._finalize_quiz(user_id, "Quiz cancelled. ")
            
        # Process as answer (A, B, C, or D)
        if len(message) == 1 and message.upper() in ["A", "B", "C", "D"]:
            return await self.process_answer(user_id, message.upper())
            
        return "Please respond with A, B, C, or D. You can also type 'hint', 'skip', or 'quit'."
    
    def _format_question(self, user_id: str) -> str:
        """Format the current question for display."""
        if user_id not in self.active_quizzes:
            return "No active quiz found. Start a new quiz with '/quiz <topic>'"
            
        quiz = self.active_quizzes[user_id]
        current_q = quiz["current_question"]
        
        if current_q >= len(quiz["questions"]):
            return "No more questions in this quiz."
            
        question = quiz["questions"][current_q]
        
        # Format question with options
        options = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(question["options"])])
        return f"Question {current_q + 1} of {len(quiz['questions'])}:\n\n{question['question']}\n\n{options}\n\nYour answer (A/B/C/D):"
    
    def _get_hint(self, user_id: str) -> str:
        """Provide a hint for the current question."""
        if user_id not in self.active_quizzes:
            return "No active quiz to provide a hint for."
            
        quiz = self.active_quizzes[user_id]
        current_q = quiz["current_question"]
        
        if current_q >= len(quiz["questions"]):
            return "The quiz is already complete."
            
        question = quiz["questions"][current_q]
        
        # Simple hint mechanism - could be enhanced with more sophisticated logic
        correct_letter = question["answer"].upper()
        hint = f"Hint: The correct answer is option {correct_letter}."
        
        return hint + "\n\n" + self._format_question(user_id)
    
    async def _skip_question(self, user_id: str) -> str:
        """Skip the current question."""
        if user_id not in self.active_quizzes:
            return "No active quiz to skip questions in."
            
        quiz = self.active_quizzes[user_id]
        
        # Record the skip
        quiz["responses"].append({
            "question_idx": quiz["current_question"],
            "answer": "SKIPPED",
            "is_correct": False,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Move to next question
        quiz["current_question"] += 1
        
        if quiz["current_question"] < len(quiz["questions"]):
            return "Question skipped.\n\n" + self._format_question(user_id)
        else:
            return await self._finalize_quiz(user_id, "Question skipped.\n\n")
    
    async def _finalize_quiz(self, user_id: str, prefix: str = "") -> str:
        """Finalize the quiz and return results."""
        if user_id not in self.active_quizzes:
            return "No active quiz to finalize."
            
        quiz = self.active_quizzes.pop(user_id, {})
        questions = quiz.get("questions", [])
        score = quiz.get("score", 0)
        total = len(questions)
        
        # Calculate score percentage
        score_pct = round((score / total) * 100) if total > 0 else 0
        
        # Generate feedback
        feedback = [
            f"{prefix}Quiz complete! 🎉",
            f"Your score: {score}/{total} ({score_pct}%)",
            ""
        ]
        
        # Add performance comment
        if score_pct >= 80:
            feedback.append("Excellent work! You have a strong understanding of this topic. 🏆")
        elif score_pct >= 60:
            feedback.append("Good job! You have a decent grasp of the material. 👍")
        else:
            feedback.append("Keep practicing! Review the material and try again. 📚")
        
        # Update user progress
        await self._update_user_progress(
            user_id=user_id,
            topic=quiz.get("topic", "general"),
            score=score_pct,
            difficulty=quiz.get("difficulty", "medium"),
            responses=quiz.get("responses", [])
        )
        
        return "\n".join(feedback)
    
    async def _update_user_progress(
        self,
        user_id: str,
        topic: str,
        score: float,
        difficulty: str,
        responses: List[Dict]
    ) -> None:
        """Update the user's progress based on quiz results."""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "quizzes_taken": 0,
                "average_score": 0,
                "topics": {},
                "recent_quizzes": []
            }
        
        user_data = self.user_progress[user_id]
        
        # Update overall stats
        total_quizzes = user_data["quizzes_taken"]
        current_avg = user_data["average_score"]
        
        user_data["quizzes_taken"] += 1
        user_data["average_score"] = (
            (current_avg * total_quizzes + score) / 
            (total_quizzes + 1)
        )
        
        # Update topic stats
        if topic not in user_data["topics"]:
            user_data["topics"][topic] = {
                "quizzes_taken": 0,
                "average_score": 0,
                "last_attempted": ""
            }
        
        topic_data = user_data["topics"][topic]
        topic_quizzes = topic_data["quizzes_taken"]
        topic_avg = topic_data["average_score"]
        
        topic_data["quizzes_taken"] += 1
        topic_data["average_score"] = (
            (topic_avg * topic_quizzes + score) / 
            (topic_quizzes + 1)
        )
        topic_data["last_attempted"] = datetime.utcnow().isoformat()
        
        # Add to recent quizzes (keep last 10)
        user_data["recent_quizzes"].append({
            "topic": topic,
            "score": score,
            "difficulty": difficulty,
            "timestamp": datetime.utcnow().isoformat(),
            "responses": responses
        })
        user_data["recent_quizzes"] = user_data["recent_quizzes"][-10:]

    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Get the quiz progress for a specific user."""
        return self.user_progress.get(user_id, {
            "quizzes_taken": 0,
            "average_score": 0,
            "topics": {},
            "recent_quizzes": []
        })

    def evaluate_quiz(self, questions: List[Dict], user_answers: List[str]) -> Dict[str, Any]:
        """
        Evaluate a set of quiz answers against the correct answers.
        
        Args:
            questions: List of question dictionaries with 'answer' key
            user_answers: List of user answers (A, B, C, or D)
            
        Returns:
            Dictionary with evaluation results
        """
        if not questions:
            return {
                "score_percent": 0,
                "correct": 0,
                "total": 0,
                "details": []
            }
            
        details = []
        correct = 0
        
        for i, (q, user_ans) in enumerate(zip(questions, user_answers)):
            is_correct = (user_ans or "").strip().upper() == q.get("answer", "").strip().upper()
            if is_correct:
                correct += 1
                
            details.append({
                "question_idx": i,
                "question": q.get("question", ""),
                "user_answer": user_ans,
                "correct_answer": q.get("answer", ""),
                "is_correct": is_correct
            })
        
        total = len(questions)
        score_pct = round((correct / total) * 100, 2) if total > 0 else 0
        
        return {
            "score_percent": score_pct,
            "correct": correct,
            "total": total,
            "details": details
        }
