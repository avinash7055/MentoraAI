from fastapi import APIRouter, Body, Query, HTTPException, Depends
from typing import Dict, Any, Optional, List
import logging

from backend.services.quiz_agent import QuizAgent
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService

# Initialize services
rag_service = RAGService()
llm_service = LLMService()
quiz_agent = QuizAgent(rag_service=rag_service, llm_service=llm_service)

router = APIRouter(prefix="/quiz", tags=["Quiz"])
logger = logging.getLogger(__name__)

@router.get("/generate")
async def generate_quiz(
    topic: str = Query(..., description="Topic for the quiz"),
    num_questions: int = Query(5, ge=1, le=20, description="Number of questions to generate"),
    difficulty: str = Query("medium", description="Difficulty level: easy, medium, or hard")
) -> Dict[str, Any]:
    """
    Generate a new quiz on the specified topic.
    """
    try:
        questions = await quiz_agent.generate_quiz(
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty.lower()
        )
        return {
            "status": "success",
            "topic": topic,
            "difficulty": difficulty,
            "questions": questions
        }
    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate")
async def evaluate_quiz(
    evaluation_data: Dict[str, Any] = Body(
        ...,
        example={
            "questions": [
                {"question": "What is the capital of France?",
                 "options": ["London", "Berlin", "Paris", "Madrid"],
                 "answer": "C"}
            ],
            "user_answers": ["C"]
        },
        description="Questions and user answers for evaluation"
    )
) -> Dict[str, Any]:
    """
    Evaluate user's answers against the correct answers.
    """
    try:
        questions = evaluation_data.get("questions", [])
        user_answers = evaluation_data.get("user_answers", [])
        
        if not questions or not user_answers:
            raise ValueError("Questions and user_answers are required")
            
        return quiz_agent.evaluate_quiz(questions, user_answers)
        
    except Exception as e:
        logger.error(f"Error evaluating quiz: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/start")
async def start_quiz(
    quiz_data: Dict[str, Any] = Body(
        ...,
        example={
            "user_id": "user123",
            "topic": "Indian History",
            "difficulty": "medium"
        }
    )
) -> Dict[str, Any]:
    """
    Start a new interactive quiz session.
    """
    try:
        user_id = quiz_data.get("user_id")
        topic = quiz_data.get("topic")
        difficulty = quiz_data.get("difficulty", "medium")
        
        if not user_id or not topic:
            raise ValueError("user_id and topic are required")
            
        response = await quiz_agent.start_quiz_session(
            user_id=user_id,
            topic=topic,
            difficulty=difficulty
        )
        
        return {
            "status": "success",
            "message": response,
            "user_id": user_id,
            "has_next_question": True
        }
        
    except Exception as e:
        logger.error(f"Error starting quiz: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/answer")
async def submit_answer(
    answer_data: Dict[str, Any] = Body(
        ...,
        example={
            "user_id": "user123",
            "answer": "A"
        }
    )
) -> Dict[str, Any]:
    """
    Submit an answer to the current quiz question.
    """
    try:
        user_id = answer_data.get("user_id")
        answer = answer_data.get("answer", "").strip()
        
        if not user_id:
            raise ValueError("user_id is required")
            
        response = await quiz_agent.process_answer(user_id, answer)
        
        return {
            "status": "success",
            "message": response,
            "user_id": user_id,
            "is_complete": not quiz_agent.active_quizzes.get(user_id, {}).get("questions")
        }
        
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/progress/{user_id}")
async def get_progress(user_id: str) -> Dict[str, Any]:
    """
    Get the quiz progress for a specific user.
    """
    try:
        progress = quiz_agent.get_user_progress(user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "progress": progress
        }
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/hint")
async def get_hint(
    hint_data: Dict[str, str] = Body(
        ...,
        example={"user_id": "user123"}
    )
) -> Dict[str, Any]:
    """
    Get a hint for the current question.
    """
    try:
        user_id = hint_data.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")
            
        hint = quiz_agent._get_hint(user_id)
        return {
            "status": "success",
            "hint": hint,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error getting hint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/skip")
async def skip_question(
    skip_data: Dict[str, str] = Body(
        ...,
        example={"user_id": "user123"}
    )
) -> Dict[str, Any]:
    """
    Skip the current question.
    """
    try:
        user_id = skip_data.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")
            
        response = await quiz_agent._skip_question(user_id)
        return {
            "status": "success",
            "message": response,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error skipping question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/end")
async def end_quiz(
    end_data: Dict[str, str] = Body(
        ...,
        example={"user_id": "user123"}
    )
) -> Dict[str, Any]:
    """
    End the current quiz session.
    """
    try:
        user_id = end_data.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")
            
        response = await quiz_agent._finalize_quiz(user_id, "Quiz ended by user. ")
        return {
            "status": "success",
            "message": response,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error ending quiz: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
