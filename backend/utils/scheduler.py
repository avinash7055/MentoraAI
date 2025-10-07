from celery import Celery
import os

celery = Celery("tasks", broker=os.getenv("REDIS_URL"))

@celery.task
def daily_reminder():
    print("Daily reminder sent to users!")
