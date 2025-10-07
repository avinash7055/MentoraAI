from sqlalchemy.orm import Session
from db.models import StudyProfile

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, user_id: str):
        profile = self.db.query(StudyProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = StudyProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
        return profile
