from celery import Celery
from .celery_config import CeleryConfig
from celery.schedules import crontab
from src.utils.config import config

bg_task = Celery(
    "src",
    include=["src.celery.task"]
)

bg_task.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Important for async tasks
    task_always_eager=False,
)

bg_task.config_from_object(CeleryConfig)
interval = config.celery_beat_interval
#configure celery beat
bg_task.conf.beat_schedule = {
        # Task 1: fetch all users_id every 30 minutes
    'get-all-users-id': {
        'task': 'src.celery.task.fetch_user_id_task',  # Task function, must be decorated with celery
        'schedule':crontab(minute=f"*/{interval}") #every 2 mins
        #
        
    },
    
}

