from fastapi import FastAPI
from routers import tutor_router, quiz_router, planner_router, tracker_router

app = FastAPI(title="AI UPSC Mentor")

# Include all agent routes
app.include_router(tutor_router.router)
app.include_router(quiz_router.router)
app.include_router(planner_router.router)
app.include_router(tracker_router.router)

@app.get("/")
def root():
    return {"message": "AI UPSC Mentor API is running 🚀"}
