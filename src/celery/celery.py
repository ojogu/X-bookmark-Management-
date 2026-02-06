from celery import Celery
from .celery_config import CeleryConfig
from celery.schedules import crontab
from src.utils.config import config

bg_task = Celery(
    "src",
    include=["src.celery.task"]
)

bg_task.conf.update(
    # Important for async tasks
    task_always_eager=False,
)

bg_task.config_from_object(CeleryConfig)
interval = config.celery_beat_interval
#configure celery beat
bg_task.conf.beat_schedule = {
        # Task 1: fetch all users_id every 30 minutes
    'get-all-front_sync_users-id': {
        'task': 'src.celery.task.fetch_user_id_for_front_sync_task',  # Task function, must be decorated with celery
        'schedule':crontab(minute=f"*/{interval}")
        }, #every 2 mins
    
    #task 2
    'get-all-backfill_users-id': {
        'task': 'src.celery.task.fetch_user_id_for_backfill_task',  # Task function, must be decorated with celery
        'schedule':crontab(minute=f"*/{interval}") #every 10 mins
        
        
    },
    
}

