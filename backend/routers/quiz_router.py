from fastapi import APIRouter, Body, Query
from services.quiz_agent import QuizAgent

router = APIRouter(prefix="/quiz", tags=["QuizAgent"])

@router.get("/generate")
def generate_quiz(topic: str = Query(...), num_questions: int = 5):
    agent = QuizAgent()
    return agent.generate_quiz(topic, num_questions)

@router.post("/evaluate")
def evaluate_quiz(
    questions: list = Body(..., description="List of quiz dicts with 'answer' key"),
    user_answers: list = Body(..., description="List of answers from user")
):
    agent = QuizAgent()
    return agent.evaluate_quiz(questions, user_answers)
