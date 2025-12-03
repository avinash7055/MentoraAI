from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, JSON, Date, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    email = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default='now()')
    last_active = Column(DateTime(timezone=True))
    preferences = Column(JSON)
    onboarding_step = Column(String(50))  # Track current onboarding step: 'exam_type', 'study_hours', 'subjects', 'completed'
    onboarding_data = Column(JSON)  # Store onboarding responses

class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default='active')
    created_at = Column(DateTime(timezone=True), server_default='now()')

class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.users.id'), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.study_plans.id'))
    subject = Column(String(100), nullable=False)
    topic = Column(String(255), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    completed = Column(Boolean, default=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default='now()')

class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.users.id'), nullable=False)
    topic = Column(String(255), nullable=False)
    difficulty = Column(String(50), nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default='now()')
    completed_at = Column(DateTime(timezone=True))
    score = Column(Integer)

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.quizzes.id'), nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct_answer = Column(String(1), nullable=False)
    explanation = Column(Text)

class UserResponse(Base):
    __tablename__ = "user_responses"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.users.id'), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.quiz_questions.id'), nullable=False)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.quizzes.id'))
    selected_option = Column(String(1), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime(timezone=True), server_default='now()')

class ProgressTracking(Base):
    __tablename__ = "progress_tracking"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.users.id'), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Numeric, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default='now()')
    details = Column(JSON)

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {'schema': 'MentoraAI'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('MentoraAI.users.id'), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default='now()')

# Keep the existing StudyProfile model for backward compatibility
class StudyProfile(Base):
    __tablename__ = "study_profiles"
    __table_args__ = {'schema': 'MentoraAI'}

    user_id = Column(String, primary_key=True, index=True)
    syllabus_completion = Column(JSON, default=dict)
    mastery = Column(JSON, default=dict)
    last_updated = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
