"""
Planner Agent for creating and managing study plans for UPSC preparation.
Helps users organize their study schedule and track progress.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from .base_agent import BaseAgent
from ..config import settings
from ..db.database import SessionLocal
from ..db.models import User, StudyPlan, Quiz
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    """Agent responsible for creating and managing study plans for UPSC aspirants."""
    
    def __init__(self):
        """Initialize the PlannerAgent with default settings."""
        super().__init__("PlannerAgent")
        self.default_study_hours = 3  # Default study hours per day
        
        # Sample UPSC syllabus topics (simplified)
        self.syllabus = {
            "Prelims": {
                "General Studies Paper I": [
                    "Indian History", "Indian and World Geography", 
                    "Indian Polity and Governance", "Economic and Social Development",
                    "Environmental Ecology", "General Science", "Current Events"
                ],
                "CSAT Paper II": [
                    "Comprehension", "Interpersonal Skills", "Logical Reasoning",
                    "Analytical Ability", "Decision Making", "General Mental Ability",
                    "Basic Numeracy", "Data Interpretation"
                ]
            },
            "Mains": {
                "Essay": ["Essay Writing"],
                "General Studies I": ["Indian Heritage and Culture", "History and Geography of the World"],
                "General Studies II": ["Governance", "Constitution", "Polity", "Social Justice", "International Relations"],
                "General Studies III": ["Technology", "Economic Development", "Biodiversity", "Security", "Disaster Management"],
                "General Studies IV": ["Ethics", "Integrity", "Aptitude"],
                "Optional Subject I": ["Chosen by the candidate"],
                "Optional Subject II": ["Chosen by the candidate"]
            },
            "Interview": ["Personality Test"]
        }
    
    async def process_message(self, phone_number: str, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a planner-related message and return an appropriate response.
        
        Args:
            phone_number: The user's phone number
            message: The user's message (plan request or update)
            context: Additional context (e.g., current plan state)
            
        Returns:
            A response message with study plan or guidance
        """
        try:
            # Parse the user's intent
            intent = self._parse_intent(message.lower())
            
            if "create" in intent or "new" in intent:
                return await self._create_study_plan(phone_number, message)
            elif "view" in intent or "show" in intent or "current" in intent:
                return await self._view_study_plan(phone_number)
            elif "update" in intent or "change" in intent:
                return await self._update_study_plan(phone_number, message)
            elif "progress" in intent or "status" in intent:
                return await self._get_study_progress(phone_number)
            else:
                return self._get_planner_help()
                
        except Exception as e:
            logger.error(f"Error in PlannerAgent: {str(e)}", exc_info=True)
            return await self.handle_error(e)
    
    async def _create_study_plan(self, phone_number: str, message: str) -> str:
        """Create a new study plan based on user preferences with interactive onboarding for new users."""
        db: Session = SessionLocal()
        try:
            # Ensure user exists
            user = self._get_or_create_user(db, phone_number)
            
            # Check if user has any existing plans (to determine if they're new)
            existing_plans = db.query(StudyPlan).filter(StudyPlan.user_id == user.id).count()
            
            # If new user and not in onboarding, start onboarding
            if existing_plans == 0 and not user.onboarding_step:
                return await self._start_onboarding(db, user)
            
            # If user is in onboarding, process their response
            if user.onboarding_step and user.onboarding_step != 'completed':
                return await self._process_onboarding_response(db, user, message)
            
            # Otherwise, create plan normally (existing user or onboarding completed)
            return await self._create_plan_from_preferences(db, user, message)
            
        except Exception as e:
            logger.error(f"Error creating study plan: {str(e)}", exc_info=True)
            return "I couldn't create your study plan. Please try again with your preferences."
        finally:
            db.close()
    
    async def _start_onboarding(self, db: Session, user: User) -> str:
        """Start the interactive onboarding flow for new users."""
        user.onboarding_step = 'exam_type'
        user.onboarding_data = {}
        db.commit()
        
        return """👋 *Welcome to MentoraAI!* 🎓

I see this is your first study plan. Let me help you get started with a personalized plan!

*Question 1 of 3:*

1️⃣ Which exam are you preparing for?
   A) Prelims 2025
   B) Mains 2025
   C) Both Prelims & Mains

Reply with *1A*, *1B*, or *1C*"""
    
    async def _process_onboarding_response(self, db: Session, user: User, message: str) -> str:
        """Process user responses during onboarding."""
        message = message.strip().upper()
        
        # Initialize onboarding_data if None
        if user.onboarding_data is None:
            user.onboarding_data = {}
        
        if user.onboarding_step == 'exam_type':
            # Parse exam type response
            if '1A' in message or 'PRELIMS' in message:
                user.onboarding_data['exam_type'] = 'Prelims 2025'
            elif '1B' in message or 'MAINS' in message:
                user.onboarding_data['exam_type'] = 'Mains 2025'
            elif '1C' in message or 'BOTH' in message:
                user.onboarding_data['exam_type'] = 'Both Prelims & Mains'
            else:
                return "❌ Invalid response. Please reply with *1A*, *1B*, or *1C*"
            
            # Move to next step
            user.onboarding_step = 'study_hours'
            db.commit()
            
            return """✅ Great choice!

*Question 2 of 3:*

2️⃣ How many hours can you study daily?
   A) 2-3 hours
   B) 4-5 hours
   C) 6+ hours

Reply with *2A*, *2B*, or *2C*"""
        
        elif user.onboarding_step == 'study_hours':
            # Parse study hours response
            if '2A' in message:
                user.onboarding_data['daily_hours'] = 3
            elif '2B' in message:
                user.onboarding_data['daily_hours'] = 5
            elif '2C' in message:
                user.onboarding_data['daily_hours'] = 7
            else:
                return "❌ Invalid response. Please reply with *2A*, *2B*, or *2C*"
            
            # Move to next step
            user.onboarding_step = 'subjects'
            db.commit()
            
            return """✅ Perfect!

*Question 3 of 3:*

3️⃣ Which subjects do you want to focus on?
   A) All subjects (balanced approach)
   B) Specific subjects (I'll ask which ones)
   C) Let the AI decide based on my quiz performance

Reply with *3A*, *3B*, or *3C*"""
        
        elif user.onboarding_step == 'subjects':
            # Parse subjects response
            if '3A' in message:
                user.onboarding_data['focus_preference'] = 'all_subjects'
                user.onboarding_data['focus_areas'] = ['General Studies', 'Current Affairs', 'Optional Subject']
            elif '3B' in message:
                user.onboarding_step = 'specific_subjects'
                db.commit()
                return """✅ Got it!

Please tell me which subjects you want to focus on. For example:
- "Polity, History, Geography"
- "Economics and Environment"
- "All GS papers"

Type your subjects:"""
            elif '3C' in message:
                user.onboarding_data['focus_preference'] = 'ai_decide'
                user.onboarding_data['focus_areas'] = ['General Studies']  # Will adapt based on quiz performance
            else:
                return "❌ Invalid response. Please reply with *3A*, *3B*, or *3C*"
            
            # Complete onboarding and generate plan
            user.onboarding_step = 'completed'
            db.commit()
            
            return await self._generate_onboarding_plan(db, user)
        
        elif user.onboarding_step == 'specific_subjects':
            # Parse specific subjects from free text
            subjects = self._parse_subjects_from_text(message)
            user.onboarding_data['focus_preference'] = 'specific_subjects'
            user.onboarding_data['focus_areas'] = subjects
            
            # Complete onboarding and generate plan
            user.onboarding_step = 'completed'
            db.commit()
            
            return await self._generate_onboarding_plan(db, user)
        
        return "Something went wrong. Please try again."
    
    def _parse_subjects_from_text(self, text: str) -> List[str]:
        """Extract subject names from user's free text."""
        text = text.lower()
        
        # Common UPSC subjects
        subject_keywords = {
            'polity': 'Indian Polity',
            'history': 'Indian History',
            'geography': 'Geography',
            'economics': 'Economics',
            'economy': 'Economics',
            'environment': 'Environment & Ecology',
            'ecology': 'Environment & Ecology',
            'science': 'General Science',
            'current affairs': 'Current Affairs',
            'csat': 'CSAT',
            'ethics': 'Ethics & Integrity',
            'international relations': 'International Relations',
            'ir': 'International Relations',
            'governance': 'Governance'
        }
        
        found_subjects = []
        for keyword, subject in subject_keywords.items():
            if keyword in text and subject not in found_subjects:
                found_subjects.append(subject)
        
        # If no subjects found, default to General Studies
        return found_subjects if found_subjects else ['General Studies']
    
    async def _generate_onboarding_plan(self, db: Session, user: User) -> str:
        """Generate study plan after onboarding is complete."""
        # Build preferences from onboarding data
        preferences = {
            'duration_weeks': 12,  # Default 12 weeks
            'daily_hours': user.onboarding_data.get('daily_hours', 3),
            'focus_areas': user.onboarding_data.get('focus_areas', ['General Studies']),
            'exam_type': user.onboarding_data.get('exam_type', 'Both'),
            'start_date': datetime.now().date().isoformat()
        }
        
        # Generate study plan
        study_plan_data = self._generate_study_plan(preferences)
        
        # Create new StudyPlan record
        new_plan = StudyPlan(
            user_id=user.id,
            title=f"Study Plan - {datetime.now().strftime('%Y-%m-%d')}",
            description=json.dumps(study_plan_data),
            start_date=datetime.fromisoformat(study_plan_data["start_date"]),
            end_date=datetime.fromisoformat(study_plan_data["end_date"]),
            status='active'
        )
        db.add(new_plan)
        db.commit()
        
        # Format the response
        response = "🎉 *Your Personalized Study Plan is Ready!* 🎉\n\n"
        response += f"🎯 *Exam Target:* {preferences['exam_type']}\n"
        response += f"📅 *Duration:* {preferences['duration_weeks']} weeks\n"
        response += f"⏰ *Daily Study Time:* {preferences['daily_hours']} hours\n"
        response += f"📚 *Focus Areas:* {', '.join(preferences['focus_areas'])}\n\n"
        
        response += "*Here's your study plan for Week 1:*\n\n"
        
        # Add first week's schedule
        for day, topics in study_plan_data["weekly_schedule"][0].items():
            response += f"*{day}:* {', '.join(topics[:2]) if topics else 'Rest'}\n"
        
        response += "\n💡 *Pro Tips:*\n"
        response += "• Type 'view plan' to see your full schedule\n"
        response += "• Take quizzes to help me identify your weak areas\n"
        response += "• I'll automatically adjust your plan based on your performance!\n\n"
        response += "Ready to start? Let's ace UPSC together! 💪"
        
        return response
    
    async def _create_plan_from_preferences(self, db: Session, user: User, message: str) -> str:
        """Create plan for existing users or after onboarding."""
        db: Session = SessionLocal()
        try:
            # Parse user preferences from message
            preferences = self._parse_preferences(message)
            
            # Ensure user exists
            user = self._get_or_create_user(db, phone_number)
            
            # Check for weak areas from Quizzes
            weak_areas = self._get_weak_areas(db, user.id)
            if weak_areas:
                preferences["weak_areas"] = weak_areas
                # Add weak areas to focus areas if not present
                for area in weak_areas:
                    if area not in preferences["focus_areas"]:
                        preferences["focus_areas"].append(area)
            
            # Generate study plan
            study_plan_data = self._generate_study_plan(preferences)
            
            # Deactivate old plans
            db.query(StudyPlan).filter(
                StudyPlan.user_id == user.id, 
                StudyPlan.status == 'active'
            ).update({"status": "archived"})
            
            # Create new StudyPlan record
            new_plan = StudyPlan(
                user_id=user.id,
                title=f"Study Plan - {datetime.now().strftime('%Y-%m-%d')}",
                description=json.dumps(study_plan_data), # Store full JSON in description for now or create a separate model
                start_date=datetime.fromisoformat(study_plan_data["start_date"]),
                end_date=datetime.fromisoformat(study_plan_data["end_date"]),
                status='active'
            )
            db.add(new_plan)
            db.commit()
            
            # Format the response
            response = "📚 *Your Study Plan Has Been Created!* 📚\n\n"
            response += f"📅 *Duration:* {preferences['duration_weeks']} weeks\n"
            response += f"⏰ *Daily Study Time:* {preferences['daily_hours']} hours\n"
            response += f"🎯 *Focus Areas:* {', '.join(preferences['focus_areas'])}\n"
            
            if weak_areas:
                response += f"⚠️ *Detected Weak Areas:* {', '.join(weak_areas)} (Prioritized in plan)\n"
            
            response += "\nHere's your study plan for the first week:\n\n"
            
            # Add first week's schedule
            for day, topics in study_plan_data["weekly_schedule"][0].items():
                response += f"*{day}:* {', '.join(topics[:2])}\n"
            
            response += "\nType 'view plan' to see your full plan or 'progress' to update your progress."
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating study plan: {str(e)}", exc_info=True)
            return "I couldn't create your study plan. Please try again with your preferences."
        finally:
            db.close()

    def _get_or_create_user(self, db: Session, phone_number: str) -> User:
        """Get existing user or create a new one."""
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            user = User(phone_number=phone_number)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def _get_weak_areas(self, db: Session, user_id: uuid.UUID) -> List[str]:
        """Identify weak areas based on quiz scores (< 50%)."""
        try:
            # Find topics with average score < 50%
            weak_topics = db.query(Quiz.topic).\
                filter(Quiz.user_id == user_id).\
                group_by(Quiz.topic).\
                having(func.avg(Quiz.score) < 3).all() # Assuming score is out of 5
            
            return [t[0] for t in weak_topics]
        except Exception:
            return []
    
    async def _view_study_plan(self, phone_number: str) -> str:
        """View the user's current study plan."""
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.phone_number == phone_number).first()
            if not user:
                return "You don't have an active study plan yet."
            
            plan_record = db.query(StudyPlan).filter(
                StudyPlan.user_id == user.id,
                StudyPlan.status == 'active'
            ).first()
            
            if not plan_record:
                return (
                    "You don't have an active study plan yet. "
                    "Would you like me to create one for you? "
                    "Just tell me your available study time and preferences."
                )
            
            # Load plan data from JSON description
            plan_data = json.loads(plan_record.description)
            # We don't have preferences stored separately in this simple model, 
            # so we might need to extract them or store them better.
            # For now, assume defaults or extract from plan_data if possible.
            duration_weeks = len(plan_data.get("weekly_schedule", []))
            
            response = (
                "📋 *Your Study Plan* 📋\n\n"
                f"📅 *Duration:* {duration_weeks} weeks\n"
                f"📅 *Start Date:* {plan_record.start_date}\n"
                f"📅 *End Date:* {plan_record.end_date}\n\n"
                "*This Week's Schedule:*\n"
            )
            
            # Get current week (0-indexed)
            # We need to recalculate current week based on start_date
            start_date = plan_record.start_date
            if isinstance(start_date, str):
                 start_date = datetime.fromisoformat(start_date).date()
            
            days_passed = (datetime.now().date() - start_date).days
            current_week = max(0, days_passed // 7)
            current_week = min(current_week, duration_weeks - 1)
            
            # Add current week's schedule
            if current_week < len(plan_data["weekly_schedule"]):
                for day, topics in plan_data["weekly_schedule"][current_week].items():
                    response += f"\n*{day}:*\n"
                    for i, topic in enumerate(topics, 1):
                        response += f"  {i}. {topic}\n"
            
            response += "\nType 'progress' to update your progress or 'update plan' to make changes."
            
            return response
            
        except Exception as e:
            logger.error(f"Error viewing study plan: {str(e)}", exc_info=True)
            return "I couldn't retrieve your study plan. Please try again later."
        finally:
            db.close()
    
    async def _update_study_plan(self, phone_number: str, message: str) -> str:
        """Update the user's study plan based on new preferences."""
        try:
            if phone_number not in self.study_plans:
                return "You don't have an active study plan. Would you like to create one?"
            
            # Parse update preferences from message
            updates = self._parse_preferences(message)
            
            # Update the plan
            plan = self.study_plans[phone_number]
            plan["preferences"].update(updates)
            plan["plan"] = self._generate_study_plan(plan["preferences"])
            plan["last_updated"] = datetime.now().isoformat()
            
            return "✅ Your study plan has been updated! Type 'view plan' to see the changes."
            
        except Exception as e:
            logger.error(f"Error updating study plan: {str(e)}", exc_info=True)
            return "I couldn't update your study plan. Please try again with your new preferences."
    
    async def _get_study_progress(self, phone_number: str) -> str:
        """Get the user's study progress."""
        try:
            plan = self.study_plans.get(phone_number)
            if not plan:
                return "You don't have an active study plan yet. Would you like to create one?"
            
            progress = plan.get("progress", {})
            prefs = plan["preferences"]
            
            # Calculate progress metrics
            total_weeks = prefs["duration_weeks"]
            current_week = self._get_current_week(plan)
            
            # Calculate completion percentage
            total_topics = sum(len(week[day]) for week in plan["plan"]["weekly_schedule"] for day in week)
            completed_topics = len(progress.get("completed_topics", []))
            completion_pct = (completed_topics / total_topics * 100) if total_topics > 0 else 0
            
            response = (
                "📊 *Your Study Progress* 📊\n\n"
                f"📅 *Week {current_week + 1} of {total_weeks}*\n"
                f"✅ *Completed Topics:* {completed_topics} of {total_topics} ({completion_pct:.1f}%)\n\n"
            )
            
            # Add streak information if available
            if "current_streak" in progress:
                response += f"🔥 *Current Streak:* {progress['current_streak']} days\n"
            
            # Add recent activity
            if "recent_activity" in progress and progress["recent_activity"]:
                response += "\n*Recent Activity:*\n"
                for activity in progress["recent_activity"][-3:]:  # Show last 3 activities
                    response += f"- {activity}\n"
            
            response += "\nTo update your progress, type 'completed [topic]' or 'skipped [topic]'."
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting study progress: {str(e)}", exc_info=True)
            return "I couldn't retrieve your study progress. Please try again later."
    
    def _parse_intent(self, message: str) -> List[str]:
        """Parse the user's intent from their message."""
        intents = []
        
        if any(word in message for word in ["create", "make", "new", "generate"]):
            intents.append("create")
        if any(word in message for word in ["view", "show", "see", "my plan"]):
            intents.append("view")
        if any(word in message for word in ["update", "change", "modify"]):
            intents.append("update")
        if any(word in message for word in ["progress", "status", "how am i doing"]):
            intents.append("progress")
        
        return intents if intents else ["help"]
    
    def _parse_preferences(self, message: str) -> Dict[str, Any]:
        """Parse study preferences from the user's message."""
        preferences = {
            "duration_weeks": 12,  # Default 12 weeks
            "daily_hours": 3,      # Default 3 hours per day
            "focus_areas": ["General Studies"],
            "start_date": datetime.now().date().isoformat()
        }
        
        # Parse duration (in weeks)
        if "week" in message:
            try:
                # Look for numbers followed by 'week' or 'weeks'
                import re
                week_match = re.search(r'(\d+)\s*week', message)
                if week_match:
                    preferences["duration_weeks"] = min(int(week_match.group(1)), 52)  # Max 1 year
            except (ValueError, AttributeError):
                pass
        
        # Parse daily study hours
        if any(word in message for word in ["hour", "hr", "hrs"]):
            try:
                # Look for numbers followed by 'hour' or 'hours'
                import re
                hour_match = re.search(r'(\d+)\s*hou?r', message)
                if hour_match:
                    preferences["daily_hours"] = min(int(hour_match.group(1)), 12)  # Max 12 hours/day
            except (ValueError, AttributeError):
                pass
        
        # Parse focus areas (simplified)
        focus_areas = []
        for paper, topics in self.syllabus.items():
            if paper.lower() in message.lower():
                focus_areas.append(paper)
            else:
                for topic in topics:
                    if topic.lower() in message.lower():
                        focus_areas.append(topic)
        
        if focus_areas:
            preferences["focus_areas"] = list(set(focus_areas))  # Remove duplicates
        
        return preferences
    
    def _generate_study_plan(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a study plan based on user preferences."""
        try:
            # Simple implementation - in a real app, this would be more sophisticated
            duration_weeks = preferences.get("duration_weeks", 12)
            daily_hours = preferences.get("daily_hours", 3)
            focus_areas = preferences.get("focus_areas", ["General Studies"])
            
            # Generate weekly schedule
            weekly_schedule = []
            
            # For each week
            for week in range(duration_weeks):
                week_plan = {
                    "Monday": [],
                    "Tuesday": [],
                    "Wednesday": [],
                    "Thursday": [],
                    "Friday": [],
                    "Saturday": [],
                    "Sunday": []
                }
                
                # Distribute focus areas across the week
                for i, area in enumerate(focus_areas):
                    day = list(week_plan.keys())[i % len(week_plan)]
                    week_plan[day].append(area)
                
                weekly_schedule.append(week_plan)
            
            return {
                "weekly_schedule": weekly_schedule,
                "total_hours": duration_weeks * 7 * daily_hours,
                "start_date": preferences.get("start_date", datetime.now().date().isoformat()),
                "end_date": (datetime.now() + timedelta(weeks=duration_weeks)).date().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating study plan: {str(e)}", exc_info=True)
            # Return a default plan in case of error
            return {
                "weekly_schedule": [{"Monday": ["General Studies"], "Tuesday": ["Current Affairs"], 
                                  "Wednesday": ["Optional Subject"], "Thursday": ["Practice Tests"], 
                                  "Friday": ["General Studies"], "Saturday": ["Revision"], 
                                  "Sunday": ["Rest/Review"]}],
                "total_hours": duration_weeks * 7 * 3,  # 3 hours/day default
                "start_date": datetime.now().date().isoformat(),
                "end_date": (datetime.now() + timedelta(weeks=12)).date().isoformat()
            }
    
    def _get_current_week(self, plan: Dict[str, Any]) -> int:
        """Calculate the current week number in the study plan."""
        try:
            start_date = datetime.fromisoformat(plan["preferences"].get("start_date", datetime.now().isoformat()))
            current_date = datetime.now()
            
            # Calculate weeks passed
            days_passed = (current_date - start_date).days
            weeks_passed = max(0, days_passed // 7)
            
            # Ensure we don't exceed total weeks
            total_weeks = plan["preferences"].get("duration_weeks", 12)
            return min(weeks_passed, total_weeks - 1)  # 0-based index
            
        except Exception as e:
            logger.error(f"Error calculating current week: {str(e)}", exc_info=True)
            return 0  # Default to first week
    
    def generate_weekly_plan(self, user_id: str) -> Dict[str, Any]:
        """
        Generate a weekly study plan for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dict containing the weekly study plan
        """
        try:
            # Check if user has an existing plan
            if user_id in self.study_plans:
                plan = self.study_plans[user_id]
                current_week = self._get_current_week(plan)
                
                # Get current week's schedule
                weekly_schedule = plan.get("weekly_schedule", {})
                current_week_plan = weekly_schedule.get(f"week_{current_week}", {})
                
                if current_week_plan:
                    return {
                        "status": "success",
                        "week_number": current_week,
                        "plan": current_week_plan,
                        "message": f"Here's your study plan for week {current_week}"
                    }
                
                # If no specific week plan exists, return the general plan
                return {
                    "status": "success",
                    "plan": plan,
                    "message": "Here's your study plan"
                }
            
            # If no plan exists, create a default one
            default_prefs = self._parse_preferences("")
            plan = self._generate_study_plan(default_prefs)
            self.study_plans[user_id] = plan
            
            return {
                "status": "success",
                "plan": plan,
                "message": "Created a new study plan for you!"
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly plan: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to generate study plan. Please try again later."
            }

    def _get_planner_help(self) -> str:
        """Get help information for the planner."""
        return (
            "📚 *Study Planner Help* 📚\n\n"
            "Here's what I can help you with:\n"
            "• *Create a study plan*: 'Create a 12-week study plan for UPSC with 3 hours daily'\n"
            "• *View your plan*: 'Show my study plan' or 'What's my schedule?'\n"
            "• *Update progress*: 'I completed Indian Polity today' or 'Mark Ancient History as done'\n"
            "• *Check progress*: 'How am I doing?' or 'Show my progress'\n\n"
            "You can also ask about specific subjects or topics you want to focus on!"
        )