from celery import Celery
from .celery_config import CeleryConfig
from celery.schedules import crontab
from src.utils.config import config
from datetime import timedelta

bg_task = Celery(
    "src",
    include=["src.celery.task"]
)

bg_task.conf.update(
    # Important for async tasks
    task_always_eager=False,
)
bg_task.conf.broker_connection_retry_on_startup = True

bg_task.config_from_object(CeleryConfig)

interval = config.celery_beat_interval
#configure celery beat
bg_task.conf.beat_schedule = {
        # Task 1: fetch all users_id every 30 minutes
    'get-all-front_sync_users-id': {
        'task': 'src.celery.task.fetch_user_id_for_front_sync_task',  # Task function, must be decorated with celery
        'schedule':timedelta(minutes=interval)
        }, #every 2 mins
    
    #task 2
    'get-all-backfill_users-id': {
        'task': 'src.celery.task.fetch_user_id_for_backfill_task',  # Task function, must be decorated with celery
        'schedule':timedelta(minutes=15) #every 10 mins
        
        
    },
    
}


# Schedule,Crontab Code,Description
# Every 2 minutes,crontab(minute='*/2'),"12:00, 12:02, 12:04..."
# Every hour at minute 2,crontab(minute=2),"12:02, 1:02, 2:02..."
# Every 2 hours,"crontab(hour='*/2', minute=0)","12:00, 2:00, 4:00..."
# Specific minutes,"crontab(minute='0,15,30,45')",Every quarter hour