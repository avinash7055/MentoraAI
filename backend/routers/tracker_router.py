from fastapi import APIRouter, Depends
from db.database import get_db
from services.tracker_agent import TrackerAgent

router = APIRouter(prefix="/tracker", tags=["TrackerAgent"])

@router.post("/update")
def update_progress(user_id: str, subject: str, delta: float, db=Depends(get_db)):
    agent = TrackerAgent(db)
    return agent.update_progress(user_id, subject, delta)

@router.get("/report")
def get_report(user_id: str, db=Depends(get_db)):
    agent = TrackerAgent(db)
    return agent.get_progress_report(user_id)
