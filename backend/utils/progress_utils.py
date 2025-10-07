from datetime import datetime

def calculate_mastery_delta(score_percent: float) -> float:
    """
    Translate quiz performance into mastery increment.
    """
    if score_percent >= 90:
        return 0.15
    elif score_percent >= 75:
        return 0.10
    elif score_percent >= 60:
        return 0.05
    else:
        return 0.01

def update_mastery(profile, subject, score_percent):
    """
    Update a user's mastery in the database.
    """
    mastery = profile.mastery or {}
    delta = calculate_mastery_delta(score_percent)
    mastery[subject] = min(1.0, mastery.get(subject, 0.0) + delta)
    profile.mastery = mastery
    profile.last_updated = datetime.utcnow()
    return profile
