from fastapi import APIRouter, Query
from services.tutor_agent import TutorAgent

router = APIRouter(prefix="/tutor", tags=["TutorAgent"])

@router.get("/answer")
def get_answer(query: str = Query(...)):
    agent = TutorAgent()
    return agent.generate_answer(query)
