from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import (
    tutor_router,
    quiz_router,
    planner_router,
    tracker_router,
    telegram_router
)
from backend.config import settings
from backend.utils.logger import setup_logging

# Set up logging
setup_logging()

app = FastAPI(
    title="AI UPSC Mentor",
    description="Multi-platform AI tutoring system for UPSC aspirants with support for Telegram and WhatsApp",
    version="1.1.0"
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
app.include_router(tutor_router.router)
app.include_router(quiz_router.router)
app.include_router(planner_router.router)
app.include_router(tracker_router.router)

# Platform-specific webhook routers
app.include_router(telegram_router.router, prefix="/telegram", tags=["telegram"])

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
