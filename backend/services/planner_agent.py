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

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    """Agent responsible for creating and managing study plans for UPSC aspirants."""
    
    def __init__(self):
        """Initialize the PlannerAgent with default settings."""
        super().__init__("PlannerAgent")
        self.study_plans = {}  # In-memory storage (replace with database in production)
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
        """Create a new study plan based on user preferences."""
        try:
            # Parse user preferences from message
            preferences = self._parse_preferences(message)
            
            # Generate study plan
            study_plan = self._generate_study_plan(preferences)
            
            # Store the plan
            self.study_plans[phone_number] = {
                "created_at": datetime.now().isoformat(),
                "preferences": preferences,
                "plan": study_plan,
                "progress": {},
                "last_updated": datetime.now().isoformat()
            }
            
            # Format the response
            response = "📚 *Your Study Plan Has Been Created!* 📚\n\n"
            response += f"📅 *Duration:* {preferences['duration_weeks']} weeks\n"
            response += f"⏰ *Daily Study Time:* {preferences['daily_hours']} hours\n"
            response += f"🎯 *Focus Areas:* {', '.join(preferences['focus_areas'])}\n\n"
            response += "Here's your study plan for the first week:\n\n"
            
            # Add first week's schedule
            for day, topics in study_plan["weekly_schedule"][0].items():
                response += f"*{day}:* {', '.join(topics[:2])}\n"
            
            response += "\nType 'view plan' to see your full plan or 'progress' to update your progress."
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating study plan: {str(e)}", exc_info=True)
            return "I couldn't create your study plan. Please try again with your preferences."
    
    async def _view_study_plan(self, phone_number: str) -> str:
        """View the user's current study plan."""
        try:
            plan = self.study_plans.get(phone_number)
            if not plan:
                return (
                    "You don't have an active study plan yet. "
                    "Would you like me to create one for you? "
                    "Just tell me your available study time and preferences."
                )
            
            prefs = plan["preferences"]
            
            response = (
                "📋 *Your Study Plan* 📋\n\n"
                f"📅 *Duration:* {prefs['duration_weeks']} weeks\n"
                f"⏰ *Daily Study Time:* {prefs['daily_hours']} hours\n"
                f"🎯 *Focus Areas:* {', '.join(prefs['focus_areas'])}\n\n"
                "*This Week's Schedule:*\n"
            )
            
            # Get current week (0-indexed)
            current_week = self._get_current_week(plan)
            
            # Add current week's schedule
            for day, topics in plan["plan"]["weekly_schedule"][current_week].items():
                response += f"\n*{day}:*\n"
                for i, topic in enumerate(topics, 1):
                    response += f"  {i}. {topic}\n"
            
            response += "\nType 'progress' to update your progress or 'update plan' to make changes."
            
            return response
            
        except Exception as e:
            logger.error(f"Error viewing study plan: {str(e)}", exc_info=True)
            return "I couldn't retrieve your study plan. Please try again later."
    
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