from celery import Celery
from .celery_config import CeleryConfig
from celery.schedules import crontab
from src.utils.config import config
from datetime import timedelta

from opentelemetry.instrumentation.celery import CeleryInstrumentor
from src.utils.telemetry import setup_telemetry 

bg_task = Celery(
    "src",
    include=["src.celery.task"]
)

bg_task.conf.update(
    task_always_eager=False,
)
bg_task.conf.broker_connection_retry_on_startup = True

bg_task.config_from_object(CeleryConfig)

# ── OpenTelemetry ─────────────────────────────────────────────────
setup_telemetry(service_name="xmarks-worker")  # distinct name from your API
CeleryInstrumentor().instrument()
# ─────────────────────────────────────────────────────────────────

interval = config.celery_beat_interval
bg_task.conf.beat_schedule = {
    'get-all-front_sync_users-id': {
        'task': 'src.celery.task.fetch_user_id_for_front_sync_task',
        'schedule': timedelta(minutes=interval)
    },
    'get-all-backfill_users-id': {
        'task': 'src.celery.task.fetch_user_id_for_backfill_task',
        'schedule': timedelta(minutes=15)
    },
}

# Schedule,Crontab Code,Description
# Every 2 minutes,crontab(minute='*/2'),"12:00, 12:02, 12:04..."
# Every hour at minute 2,crontab(minute=2),"12:02, 1:02, 2:02..."
# Every 2 hours,"crontab(hour='*/2', minute=0)","12:00, 2:00, 4:00..."
# Specific minutes,"crontab(minute='0,15,30,45')",Every quarter hour