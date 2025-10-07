from sqlalchemy import Column, String, Float, JSON, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class StudyProfile(Base):
    __tablename__ = "study_profiles"
    user_id = Column(String, primary_key=True, index=True)
    syllabus_completion = Column(JSON, default={})
    mastery = Column(JSON, default={})
    last_updated = Column(TIMESTAMP, default=datetime.datetime.utcnow)
