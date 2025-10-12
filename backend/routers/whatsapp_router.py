from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import User, StudyProfile
from backend.services.whatsapp_service import whatsapp_service
from backend.services.message_processor import message_processor
from backend.services.quiz_agent import QuizAgent
from backend.services.planner_agent import PlannerAgent
from backend.services.tutor_agent import TutorAgent

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize agents
quiz_agent = QuizAgent()
planner_agent = PlannerAgent()
tutor_agent = TutorAgent()

def get_or_create_user(db: Session, phone_number: str, name: Optional[str] = None) -> User:
    """Get existing user or create a new one if not exists"""
    # Clean phone number (remove any non-digit characters and add @c.us if not present)
    phone_number = ''.join(c for c in phone_number if c.isdigit())
    if not phone_number.endswith('@c.us'):
        phone_number = f"{phone_number}@c.us"
    
    # Check if user exists
    user = db.query(User).filter(User.phone_number == phone_number).first()
    
    if not user:
        # Create new user
        user = User(
            phone_number=phone_number,
            name=name or f"User-{phone_number[:5]}",
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create user's study profile
        profile = StudyProfile(
            user_id=user.id,
            syllabus_completion={},
            mastery={},
            last_updated=datetime.utcnow()
        )
        db.add(profile)
        db.commit()
        
        logger.info(f"Created new user: {user.id} ({phone_number})")
    else:
        # Update last active time
        user.last_active = datetime.utcnow()
        db.commit()
    
    return user

async def route_message_to_agent(user_id: str, intent: str, entities: Dict[str, Any], original_message: str) -> str:
    """Route message to appropriate agent based on intent"""
    
    # Check if user has an active quiz session
    if user_id in quiz_agent.active_quizzes:
        return await handle_quiz_answer(user_id, original_message)
    
    if intent == "quiz":
        topic = entities.get("primary_subject", "general")
        difficulty = entities.get("difficulty", "medium")
        num_questions = entities.get("num_questions", 5)
        
        # Start quiz session
        questions = await quiz_agent.generate_quiz(
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty
        )
        
        if questions:
            # Store quiz session for user
            quiz_agent.active_quizzes[user_id] = {
                "questions": questions,
                "current_question": 0,
                "score": 0,
                "responses": [],
                "topic": topic,
                "difficulty": difficulty,
                "start_time": datetime.utcnow().isoformat()
            }
            
            return quiz_agent._format_question(user_id)
        else:
            return "Sorry, I couldn't generate a quiz right now. Please try again with a different topic!"
    
    elif intent == "plan":
        subject = entities.get("primary_subject", "general")
        duration = entities.get("duration", "1 month")
        
        # Generate study plan
        plan_response = await planner_agent.process_message(user_id, f"Create a {duration} study plan for {subject}")
        return plan_response
    
    elif intent == "tutor":
        # Route to tutor agent for explanations
        explanation = await tutor_agent.process_message(user_id, original_message)
        return explanation
    
    elif intent == "track":
        # Generate progress report
        # For now, return a placeholder
        return "📊 **Your Progress Report:**\n\n• Total Study Sessions: 5\n• Average Score: 78%\n• Current Streak: 3 days\n• Top Subject: Polity (85%)\n\nKeep up the great work! 🎯"
    
    elif intent == "help":
        return message_processor.get_default_response("help")
    
    elif intent == "greeting":
        return message_processor.get_default_response("greeting")
    
    elif intent == "thanks":
        return message_processor.get_default_response("thanks")
    
    else:
        # Unknown intent - provide help
        return ("I didn't understand that. Here's what I can help you with:\n\n"
                "• 📚 Take a quiz: 'Quiz me on Polity'\n"
                "• 📅 Study planning: 'Create a study plan'\n"
                "• ❓ Ask questions: 'Explain Article 370'\n"
                "• 📊 Check progress: 'Show my progress'\n"
                "• 🆘 Get help: 'Help'\n\n"
                "What would you like to do?")

async def handle_quiz_answer(user_id: str, answer: str) -> str:
    """Handle quiz answer and continue quiz session"""
    try:
        # Get current quiz session
        quiz_data = quiz_agent.active_quizzes.get(user_id)
        if not quiz_data:
            return "No active quiz found. Start a new quiz: 'Quiz me on [topic]'"
        
        questions = quiz_data["questions"]
        current_q = quiz_data["current_question"]
        
        if current_q >= len(questions):
            # Quiz completed - show results
            score = quiz_data["score"]
            total = len(questions)
            percentage = (score / total * 100) if total > 0 else 0
            
            # Clean up quiz session
            del quiz_agent.active_quizzes[user_id]
            
            return (f"🎉 Quiz Complete! 🎉\n\n"
                   f"Final Score: {score}/{total} ({percentage:.1f}%)\n\n"
                   "Great job! Would you like to:\n"
                   "• Take another quiz: 'Quiz me on [topic]'\n"
                   "• Review mistakes: 'Show my answers'\n"
                   "• Try a different subject: 'Quiz on History'")
        
        # Get current question
        question = questions[current_q]
        correct_answer = question.get("answer", "").upper()
        
        # Validate answer format
        answer = answer.strip().upper()
        if answer not in ["A", "B", "C", "D"]:
            return ("Please reply with A, B, C, or D.\n\n" + quiz_agent._format_question(user_id))
        
        # Check if answer is correct
        is_correct = (answer == correct_answer)
        if is_correct:
            quiz_data["score"] += 1
        
        # Store response
        quiz_data["responses"].append({
            "question_idx": current_q,
            "user_answer": answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct
        })
        
        # Move to next question
        quiz_data["current_question"] += 1
        
        # Check if quiz is complete
        if quiz_data["current_question"] >= len(questions):
            # Show final results
            score = quiz_data["score"]
            total = len(questions)
            percentage = (score / total * 100) if total > 0 else 0
            
            # Clean up quiz session
            del quiz_agent.active_quizzes[user_id]
            
            return (f"🎉 Quiz Complete! 🎉\n\n"
                   f"Final Score: {score}/{total} ({percentage:.1f}%)\n\n"
                   "Great job! Would you like to:\n"
                   "• Take another quiz: 'Quiz me on [topic]'\n"
                   "• Review mistakes: 'Show my answers'\n"
                   "• Try a different subject: 'Quiz on History'")
        
        # Show next question
        return quiz_agent._format_question(user_id)
        
    except Exception as e:
        logger.error(f"Error handling quiz answer: {str(e)}")
        return "Sorry, there was an error processing your answer. Please try starting a new quiz."

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str,
    hub_verify_token: str,
    hub_challenge: str,
    db: Session = Depends(get_db)
):
    """Verify webhook for WhatsApp Business API"""
    if hub_verify_token == settings.VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid verify token")

@router.post("/webhook")
async def webhook_handler(request: Request, db: Session = Depends(get_db)):
    """Handle incoming WhatsApp messages"""
    try:
        data = await request.json()
        logger.debug(f"Received webhook data: {data}")

        if data.get("object") != "whatsapp_business_account":
            return {"status": "ignored"}

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    message_data = change.get("value", {})
                    
                    # Extract message details
                    contacts = message_data.get("contacts", [{}])
                    contact = contacts[0] if contacts else {}
                    
                    messages = message_data.get("messages", [{}])
                    message = messages[0] if messages else {}
                    
                    # Get user phone number and message text
                    from_number = message.get("from")
                    message_text = message.get("text", {}).get("body", "")
                    
                    if not from_number:
                        logger.warning("No phone number in message")
                        continue
                    
                    # Get or create user
                    user = get_or_create_user(
                        db=db,
                        phone_number=from_number,
                        name=contact.get("profile", {}).get("name")
                    )
                    
                    # Detect intent using AI classifier
                    intent, intent_data = message_processor.detect_intent(message_text)
                    
                    logger.info(f"Message from {user.id} ({from_number}): '{message_text}' -> Intent: {intent}")
                    
                    # Route to appropriate agent
                    response = await route_message_to_agent(user.id, intent, intent_data, message_text)
                    
                    # Send response back to user
                    await whatsapp_service.send_message(
                        to=user.phone_number,
                        message=response
                    )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing message"
        )
