"""
Onboarding Service for handling new user registration and profile setup.
Collects: Name, Email, Exam Type, Study Hours, Focus Areas
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..db.models import User
from datetime import datetime

logger = logging.getLogger(__name__)

class OnboardingService:
    """Handles the multi-step onboarding flow for new users."""
    
    def __init__(self):
        self.steps = ['name', 'email', 'exam_type', 'study_hours', 'subjects', 'completed']
    
    async def process_onboarding_message(self, db: Session, user: User, message: str) -> str:
        """
        Process a message during onboarding and return the appropriate response.
        
        Args:
            db: Database session
            user: User object
            message: User's message
            
        Returns:
            Response message for the user
        """
        if not user.onboarding_step or user.onboarding_step == 'completed':
            return None
        
        # Initialize onboarding_data if None
        if user.onboarding_data is None:
            user.onboarding_data = {}
        
        current_step = user.onboarding_step
        
        if current_step == 'name':
            return await self._process_name(db, user, message)
        elif current_step == 'email':
            return await self._process_email(db, user, message)
        elif current_step == 'exam_type':
            return await self._process_exam_type(db, user, message)
        elif current_step == 'study_hours':
            return await self._process_study_hours(db, user, message)
        elif current_step == 'subjects':
            return await self._process_subjects(db, user, message)
        elif current_step == 'specific_subjects':
            return await self._process_specific_subjects(db, user, message)
        
        return "Something went wrong. Please type /start to restart."
    
    async def _process_name(self, db: Session, user: User, message: str) -> str:
        """Process name input."""
        name = message.strip()
        
        if len(name) < 2:
            return "❌ Please enter a valid name (at least 2 characters)."
        
        # Save name
        user.name = name
        user.onboarding_data['name'] = name
        user.onboarding_step = 'email'
        db.commit()
        
        return f"""✅ Nice to meet you, {name}!

*Question 2 of 5:*

What's your email address? 📧

(This helps us send you study materials and updates)

Type your email or type *skip* if you prefer not to share."""
    
    async def _process_email(self, db: Session, user: User, message: str) -> str:
        """Process email input."""
        message = message.strip().lower()
        
        if message == 'skip':
            user.email = None
            user.onboarding_data['email'] = None
        else:
            # Basic email validation
            if '@' not in message or '.' not in message:
                return "❌ Please enter a valid email address or type *skip*."
            
            user.email = message
            user.onboarding_data['email'] = message
        
        user.onboarding_step = 'exam_type'
        db.commit()
        
        return """✅ Great!

*Question 3 of 5:*

Which exam are you preparing for? 🎯

1️⃣ Prelims 2025
2️⃣ Mains 2025
3️⃣ Both Prelims & Mains

Reply with *1*, *2*, or *3*"""
    
    async def _process_exam_type(self, db: Session, user: User, message: str) -> str:
        """Process exam type selection."""
        message = message.strip()
        
        exam_mapping = {
            '1': 'Prelims 2025',
            '2': 'Mains 2025',
            '3': 'Both Prelims & Mains',
            'prelims': 'Prelims 2025',
            'mains': 'Mains 2025',
            'both': 'Both Prelims & Mains'
        }
        
        exam_type = exam_mapping.get(message.lower())
        
        if not exam_type:
            return "❌ Invalid choice. Please reply with *1*, *2*, or *3*"
        
        user.onboarding_data['exam_type'] = exam_type
        user.onboarding_step = 'study_hours'
        db.commit()
        
        return f"""✅ Excellent! Preparing for {exam_type}

*Question 4 of 5:*

How many hours can you dedicate to UPSC preparation daily? ⏰

1️⃣ 2-3 hours
2️⃣ 4-5 hours
3️⃣ 6+ hours

Reply with *1*, *2*, or *3*"""
    
    async def _process_study_hours(self, db: Session, user: User, message: str) -> str:
        """Process study hours selection."""
        message = message.strip()
        
        hours_mapping = {
            '1': 3,
            '2': 5,
            '3': 7
        }
        
        daily_hours = hours_mapping.get(message)
        
        if not daily_hours:
            return "❌ Invalid choice. Please reply with *1*, *2*, or *3*"
        
        user.onboarding_data['daily_hours'] = daily_hours
        user.onboarding_step = 'subjects'
        db.commit()
        
        return f"""✅ Perfect! {daily_hours} hours daily is a great commitment!

*Question 5 of 5:*

Which subjects do you want to focus on? 📚

1️⃣ All subjects (balanced approach)
2️⃣ Specific subjects (I'll ask which ones)
3️⃣ Let the AI decide based on my quiz performance

Reply with *1*, *2*, or *3*"""
    
    async def _process_subjects(self, db: Session, user: User, message: str) -> str:
        """Process subject preference selection."""
        message = message.strip()
        
        if message == '1':
            user.onboarding_data['focus_preference'] = 'all_subjects'
            user.onboarding_data['focus_areas'] = ['General Studies', 'Current Affairs', 'Optional Subject']
            return await self._complete_onboarding(db, user)
        
        elif message == '2':
            user.onboarding_step = 'specific_subjects'
            db.commit()
            return """✅ Got it!

Please tell me which subjects you want to focus on. For example:
• "Polity, History, Geography"
• "Economics and Environment"
• "All GS papers"

Type your subjects:"""
        
        elif message == '3':
            user.onboarding_data['focus_preference'] = 'ai_decide'
            user.onboarding_data['focus_areas'] = ['General Studies']
            return await self._complete_onboarding(db, user)
        
        else:
            return "❌ Invalid choice. Please reply with *1*, *2*, or *3*"
    
    async def _process_specific_subjects(self, db: Session, user: User, message: str) -> str:
        """Process specific subject names from free text."""
        subjects = self._parse_subjects_from_text(message)
        user.onboarding_data['focus_preference'] = 'specific_subjects'
        user.onboarding_data['focus_areas'] = subjects
        
        return await self._complete_onboarding(db, user)
    
    def _parse_subjects_from_text(self, text: str) -> list:
        """Extract subject names from user's free text."""
        text = text.lower()
        
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
        
        return found_subjects if found_subjects else ['General Studies']
    
    async def _complete_onboarding(self, db: Session, user: User) -> str:
        """Complete the onboarding process."""
        user.onboarding_step = 'completed'
        user.last_active = datetime.utcnow()
        db.commit()
        
        name = user.name or "there"
        exam_type = user.onboarding_data.get('exam_type', 'UPSC')
        daily_hours = user.onboarding_data.get('daily_hours', 3)
        focus_areas = user.onboarding_data.get('focus_areas', ['General Studies'])
        
        return f"""🎉 *Welcome aboard, {name}!* 🎉

Your profile is all set up! Here's what I know about you:

🎯 *Target:* {exam_type}
⏰ *Daily Study Time:* {daily_hours} hours
📚 *Focus Areas:* {', '.join(focus_areas)}

*What's Next?*

I'm ready to help you ace UPSC! Here's what you can do:

• 📝 *Start a Quiz*: Type "quiz me on Polity"
• 📅 *Create Study Plan*: Type "create a study plan"
• 🧠 *Ask Questions*: Just ask any UPSC topic
• 📊 *Track Progress*: Type "show my progress"

Type /help anytime to see all commands.

*Let's begin your UPSC journey!* 💪"""

# Create singleton instance
onboarding_service = OnboardingService()
