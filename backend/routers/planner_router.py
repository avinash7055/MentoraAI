from fastapi import APIRouter, Depends
from db.database import get_db
from services.planner_agent import PlannerAgent

router = APIRouter(prefix="/planner", tags=["PlannerAgent"])

@router.get("/generate")
def generate_plan(user_id: str, db=Depends(get_db)):
    agent = PlannerAgent(db)
    return agent.generate_weekly_plan(user=user_id)
