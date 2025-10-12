"""
Tracker Agent for monitoring and analyzing study progress and performance.
Helps users track their UPSC preparation metrics and provides insights.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

from .base_agent import BaseAgent
from ..config import settings

logger = logging.getLogger(__name__)

class TrackerAgent(BaseAgent):
    """Agent responsible for tracking study progress and performance metrics."""
    
    def __init__(self):
        """Initialize the TrackerAgent with default settings."""
        super().__init__("TrackerAgent")
        self.study_sessions = {}  # In-memory storage (replace with database in production)
        self.performance_metrics = {}
        
        # Default tracking categories
        self.categories = {
            "study_time": "⏱️ Study Time",
            "topics_covered": "📚 Topics Covered",
            "practice_tests": "📝 Practice Tests",
            "revision_sessions": "🔄 Revision Sessions",
            "mcq_accuracy": "🎯 MCQ Accuracy"
        }
    
    async def process_message(self, phone_number: str, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a tracking-related message and return an appropriate response.
        
        Args:
            phone_number: The user's phone number
            message: The user's message (tracking update or query)
            context: Additional context (e.g., current tracking state)
            
        Returns:
            A response message with tracking information or confirmation
        """
        try:
            # Parse the user's intent
            intent = self._parse_intent(message.lower())
            
            if "log" in intent or "add" in intent or "update" in intent:
                return await self._log_study_session(phone_number, message)
            elif "view" in intent or "show" in intent or "my" in intent:
                return await self._view_progress(phone_number, message)
            elif "stats" in intent or "analytics" in intent:
                return await self._get_analytics(phone_number)
            elif "goal" in intent or "target" in intent:
                return await self._manage_goals(phone_number, message)
            else:
                return self._get_tracker_help()
                
        except Exception as e:
            logger.error(f"Error in TrackerAgent: {str(e)}", exc_info=True)
            return await self.handle_error(e)
    
    async def _log_study_session(self, phone_number: str, message: str) -> str:
        """Log a new study session or update an existing one."""
        try:
            # Parse study session details from message
            session_data = self._parse_session_data(message)
            
            # Initialize user data if not exists
            if phone_number not in self.study_sessions:
                self.study_sessions[phone_number] = []
                self.performance_metrics[phone_number] = self._get_default_metrics()
            
            # Add timestamp if not provided
            if "timestamp" not in session_data:
                session_data["timestamp"] = datetime.now().isoformat()
            
            # Store the session
            self.study_sessions[phone_number].append(session_data)
            
            # Update performance metrics
            self._update_metrics(phone_number, session_data)
            
            # Generate confirmation message
            response = "✅ *Study Session Logged!*\n\n"
            
            if "duration" in session_data:
                response += f"⏱️ *Duration:* {session_data['duration']} minutes\n"
            if "topic" in session_data:
                response += f"📚 *Topic:* {session_data['topic']}\n"
            if "notes" in session_data:
                response += f"📝 *Notes:* {session_data['notes']}\n"
            
            response += "\nKeep up the good work! 💪"
            
            return response
            
        except Exception as e:
            logger.error(f"Error logging study session: {str(e)}", exc_info=True)
            return "I couldn't log your study session. Please try again with the format: 'Studied [topic] for [duration] minutes'"
    
    async def _view_progress(self, phone_number: str, message: str) -> str:
        """View the user's study progress and statistics."""
        try:
            if phone_number not in self.study_sessions or not self.study_sessions[phone_number]:
                return "You haven't logged any study sessions yet. Start by saying 'I studied [topic] for [duration] minutes'"
            
            # Get user's metrics
            metrics = self.performance_metrics.get(phone_number, self._get_default_metrics())
            
            # Calculate time-based statistics
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            daily_time = sum(
                s.get("duration", 0) 
                for s in self.study_sessions[phone_number] 
                if datetime.fromisoformat(s["timestamp"]).date() == today
            )
            
            weekly_time = sum(
                s.get("duration", 0)
                for s in self.study_sessions[phone_number]
                if datetime.fromisoformat(s["timestamp"]).date() >= week_start
            )
            
            total_time = sum(s.get("duration", 0) for s in self.study_sessions[phone_number])
            
            # Generate progress report
            response = (
                "📊 *Your Study Progress* 📊\n\n"
                f"📅 *Today's Study Time:* {daily_time} minutes\n"
                f"📅 *This Week's Total:* {weekly_time} minutes\n"
                f"📅 *Total Study Time:* {total_time} minutes\n\n"
                "*📚 Topics Covered This Week:*\n"
            )
            
            # Get recent topics
            recent_topics = {}
            for session in reversed(self.study_sessions[phone_number][-10:]):  # Last 10 sessions
                topic = session.get("topic", "Unknown Topic")
                duration = session.get("duration", 0)
                if topic in recent_topics:
                    recent_topics[topic] += duration
                else:
                    recent_topics[topic] = duration
            
            for topic, duration in list(recent_topics.items())[:5]:  # Top 5 recent topics
                response += f"• {topic}: {duration} minutes\n"
            
            # Add goal progress if any
            if "goals" in metrics and metrics["goals"]:
                response += "\n*🎯 Goals Progress:*\n"
                for goal_name, goal in metrics["goals"].items():
                    progress = min(goal.get("current", 0) / goal["target"] * 100, 100)
                    response += f"• {goal_name}: {progress:.1f}% complete\n"
            
            response += "\nType 'analytics' for detailed statistics or 'log' to add a new session."
            
            return response
            
        except Exception as e:
            logger.error(f"Error viewing progress: {str(e)}", exc_info=True)
            return "I couldn't retrieve your progress. Please try again later."
    
    async def _get_analytics(self, phone_number: str) -> str:
        """Generate detailed analytics and insights from the user's study data."""
        try:
            if phone_number not in self.study_sessions or not self.study_sessions[phone_number]:
                return "You haven't logged any study sessions yet. Start by saying 'I studied [topic] for [duration] minutes'"
            
            metrics = self.performance_metrics.get(phone_number, self._get_default_metrics())
            
            # Calculate time distribution by day of week
            day_distribution = {}
            for session in self.study_sessions[phone_number]:
                day = datetime.fromisoformat(session["timestamp"]).strftime("%A")
                duration = session.get("duration", 0)
                if day in day_distribution:
                    day_distribution[day] += duration
                else:
                    day_distribution[day] = duration
            
            # Calculate most productive time of day
            time_distribution = {"Morning (6AM-12PM)": 0, "Afternoon (12PM-5PM)": 0, 
                               "Evening (5PM-10PM)": 0, "Night (10PM-6AM)": 0}
            
            for session in self.study_sessions[phone_number]:
                hour = datetime.fromisoformat(session["timestamp"]).hour
                duration = session.get("duration", 0)
                
                if 6 <= hour < 12:
                    time_distribution["Morning (6AM-12PM)"] += duration
                elif 12 <= hour < 17:
                    time_distribution["Afternoon (12PM-5PM)"] += duration
                elif 17 <= hour < 22:
                    time_distribution["Evening (5PM-10PM)"] += duration
                else:
                    time_distribution["Night (10PM-6AM)"] += duration
            
            # Generate analytics report
            response = (
                "📈 *Your Study Analytics* 📈\n\n"
                "*📅 Study Time by Day:*\n"
            )
            
            # Add day distribution
            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                minutes = day_distribution.get(day, 0)
                hours = minutes / 60
                response += f"• {day[:3]}: {minutes} min ({hours:.1f} hrs)\n"
            
            response += "\n*⏰ Most Productive Time of Day:*\n"
            
            # Add time distribution
            for time_slot, minutes in time_distribution.items():
                hours = minutes / 60
                response += f"• {time_slot}: {minutes} min ({hours:.1f} hrs)\n"
            
            # Add streak information
            current_streak = metrics.get("current_streak", 0)
            longest_streak = metrics.get("longest_streak", 0)
            
            response += (
                f"\n*🔥 Current Streak:* {current_streak} days\n"
                f"*🏆 Longest Streak:* {longest_streak} days\n\n"
            )
            
            # Add insights
            response += "*💡 Insights & Tips:*\n"
            
            # Generate insights based on data
            if time_distribution["Morning (6AM-12PM)"] > time_distribution["Evening (5PM-10PM)"]:
                response += "• You're a morning person! Your most productive hours are before noon.\n"
            else:
                response += "• You're more productive in the evenings. Try to schedule challenging topics during this time.\n"
            if current_streak >= 3:
                response += f"• Great job on your {current_streak}-day study streak! Consistency is key to success.\n"
            response += "\nKeep up the good work! 🚀"
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating analytics: {str(e)}", exc_info=True)
            return "I couldn't generate your analytics. Please try again later."
    
    async def _manage_goals(self, phone_number: str, message: str) -> str:
        """Manage study goals (set, update, or view)."""
        try:
            if phone_number not in self.performance_metrics:
                self.performance_metrics[phone_number] = self._get_default_metrics()
            
            metrics = self.performance_metrics[phone_number]
            
            # Initialize goals if not exists
            if "goals" not in metrics:
                metrics["goals"] = {}
            
            # Parse goal command
            if "set" in message.lower() or "create" in message.lower():
                # Parse goal details from message
                goal_name = "Study Time"  # Default goal name
                target = 60  # Default target (60 minutes)
                
                # Look for numbers in the message
                import re
                number_match = re.search(r'(\d+)', message)
                if number_match:
                    target = int(number_match.group(1))
                
                # Look for goal name
                name_match = re.search(r'goal (?:to|for) (.+?) (?:for|in)', message.lower())
                if name_match:
                    goal_name = name_match.group(1).title()
                
                # Create or update goal
                metrics["goals"][goal_name] = {
                    "target": target,
                    "current": 0,
                    "unit": "minutes",
                    "created_at": datetime.now().isoformat()
                }
                
                return f"✅ Goal set! {goal_name}: 0/{target} minutes"
                
            elif "update" in message.lower() or "progress" in message.lower():
                # Update goal progress
                # This is a simplified version - in a real app, you'd parse which goal to update
                if not metrics["goals"]:
                    return "You don't have any goals set yet. Say 'set a goal to study [X] minutes per day'"
                
                # For simplicity, update the first goal
                goal_name = next(iter(metrics["goals"]))
                goal = metrics["goals"][goal_name]
                
                # Look for numbers in the message
                import re
                number_match = re.search(r'(\d+)', message)
                if number_match:
                    progress = int(number_match.group(1))
                    goal["current"] = min(goal["current"] + progress, goal["target"])
                    
                    percentage = (goal["current"] / goal["target"]) * 100
                    return f"✅ Progress updated! {goal_name}: {goal['current']}/{goal['target']} minutes ({percentage:.1f}%)"
                else:
                    return "Please specify how much progress you've made (e.g., 'I studied 30 minutes')"
                
            else:
                # View goals
                if not metrics["goals"]:
                    return "You don't have any goals set yet. Say 'set a goal to study [X] minutes per day'"
                
                response = "🎯 *Your Study Goals* 🎯\n\n"
                
                for name, goal in metrics["goals"].items():
                    percentage = (goal["current"] / goal["target"]) * 100
                    response += (
                        f"*{name}*\n"
                        f"Progress: {goal['current']}/{goal['target']} {goal.get('unit', 'minutes')} ({percentage:.1f}%)\n"
                        f"Set on: {datetime.fromisoformat(goal['created_at']).strftime('%b %d, %Y')}\n\n"
                    )
                
                response += "To update progress, say 'I studied [X] minutes today'"
                return response
                
        except Exception as e:
            logger.error(f"Error managing goals: {str(e)}", exc_info=True)
            return "I couldn't process your goal request. Please try again with the format: 'Set a goal to study [X] minutes per day'"
    
    def _parse_intent(self, message: str) -> List[str]:
        """Parse the user's intent from their message."""
        intents = []
        
        if any(word in message for word in ["log", "add", "studied", "completed"]):
            intents.append("log")
        if any(word in message for word in ["view", "show", "my progress", "my stats"]):
            intents.append("view")
        if any(word in message for word in ["analytics", "stats", "insights"]):
            intents.append("analytics")
        if any(word in message for word in ["goal", "target", "objective"]):
            intents.append("goal")
        
        return intents if intents else ["help"]
    
    def _parse_session_data(self, message: str) -> Dict[str, Any]:
        """Parse study session data from the user's message."""
        session_data = {}
        
        # Look for duration (e.g., "30 minutes", "2 hours")
        import re
        
        # Match duration in minutes
        min_match = re.search(r'(\d+)\s*(?:min|minutes|mins|m)\b', message.lower())
        if min_match:
            session_data["duration"] = int(min_match.group(1))
        else:
            # Match duration in hours
            hr_match = re.search(r'(\d+)\s*(?:hr|hour|hours|h)\b', message.lower())
            if hr_match:
                session_data["duration"] = int(hr_match.group(1)) * 60
        
        # Extract topic (text between "studied" and "for" or end of string)
        topic_match = re.search(r'(?:studied|completed|revised|read|learned)\s+(.+?)(?:\s+for\s|\s*$)', message.lower())
        if topic_match:
            session_data["topic"] = topic_match.group(1).strip().title()
        
        # Extract notes (text after "notes:")
        notes_match = re.search(r'notes?:\s*(.+)', message, re.IGNORECASE)
        if notes_match:
            session_data["notes"] = notes_match.group(1).strip()
        
        return session_data
    
    def _update_metrics(self, phone_number: str, session_data: Dict[str, Any]) -> None:
        """Update performance metrics based on the logged session."""
        if phone_number not in self.performance_metrics:
            self.performance_metrics[phone_number] = self._get_default_metrics()
        
        metrics = self.performance_metrics[phone_number]
        
        # Update total study time
        metrics["total_study_time"] = metrics.get("total_study_time", 0) + session_data.get("duration", 0)
        
        # Update topic count
        topic = session_data.get("topic", "Unknown Topic")
        if "topics" not in metrics:
            metrics["topics"] = {}
        metrics["topics"][topic] = metrics["topics"].get(topic, 0) + session_data.get("duration", 0)
        
        # Update streak
        self._update_streak(phone_number, datetime.fromisoformat(session_data["timestamp"]))
        
        # Update last session timestamp
        metrics["last_session"] = session_data["timestamp"]
    
    def _update_streak(self, phone_number: str, session_time: datetime) -> None:
        """Update the user's study streak."""
        metrics = self.performance_metrics[phone_number]
        
        # Initialize streak if not exists
        if "current_streak" not in metrics:
            metrics["current_streak"] = 0
        if "longest_streak" not in metrics:
            metrics["longest_streak"] = 0
        if "last_study_day" not in metrics:
            metrics["last_study_day"] = None
        
        # Get dates for comparison
        today = session_time.date()
        last_study_day = (
            datetime.fromisoformat(metrics["last_study_day"]).date() 
            if metrics["last_study_day"] 
            else None
        )
        
        # Update streak
        if last_study_day is None:
            # First study session
            metrics["current_streak"] = 1
        elif last_study_day == today - timedelta(days=1):
            # Consecutive days
            metrics["current_streak"] += 1
        elif last_study_day < today - timedelta(days=1):
            # Streak broken
            metrics["current_streak"] = 1
        # else: same day, don't update streak
        
        # Update longest streak if needed
        if metrics["current_streak"] > metrics["longest_streak"]:
            metrics["longest_streak"] = metrics["current_streak"]
        
        # Update last study day
        metrics["last_study_day"] = today.isoformat()
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """Get default metrics for a new user."""
        return {
            "total_study_time": 0,
            "topics": {},
            "current_streak": 0,
            "longest_streak": 0,
            "last_study_day": None,
            "goals": {},
            "created_at": datetime.now().isoformat()
        }
    
    def _get_tracker_help(self) -> str:
        """Get help information for the tracker."""
        return (
            "📊 *Study Tracker Help* 📊\n\n"
            "Here's what you can do:\n"
            "• *Log study time*: 'Studied Indian Polity for 45 minutes'\n"
            "• *View progress*: 'Show my progress' or 'How am I doing?'\n"
            "• *Get analytics*: 'Show me my stats' or 'Analytics'\n"
            "• *Set goals*: 'Set a goal to study 2 hours daily'\n"
            "• *Update goals*: 'I studied 30 minutes today'\n\n"
            "Example commands:\n"
            "• 'I studied Modern History for 2 hours today. Notes: Covered Indian National Movement'\n"
            "• 'Show me my study analytics'\n"
            "• 'Set a goal to complete 50 practice tests this month'"
        )