from fastapi import APIRouter, Query, HTTPException
from backend.services.tutor_agent import TutorAgent

router = APIRouter(prefix="/tutor", tags=["TutorAgent"])

@router.get("/answer")
async def get_answer(query: str = Query(..., description="The question to get an answer for")):
    """
    Get an answer to an educational question.
    """
    try:
        agent = TutorAgent()
        answer = await agent.generate_answer(query)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
