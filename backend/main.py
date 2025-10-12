from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import (
    tutor_router,
    quiz_router,
    planner_router,
    tracker_router,
    webhook_router,
    whatsapp_router
)
from backend.utils.logger import setup_logging

# Set up logging
setup_logging()

app = FastAPI(
    title="AI UPSC Mentor",
    description="WhatsApp-based multi-agent tutoring system for UPSC aspirants",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
app.include_router(webhook_router.router)
app.include_router(tutor_router.router)
app.include_router(quiz_router.router)
app.include_router(planner_router.router)
app.include_router(tracker_router.router)
app.include_router(whatsapp_router.router)  # WhatsApp webhook router

@app.get("/")
def root():
    """Root endpoint that returns a welcome message."""
    return {
        "message": "AI UPSC Mentor API is running 🚀",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    # TODO: Add database and external service health checks
    return {"status": "ok"}
