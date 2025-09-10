

from kombu import Queue
from src.utils.config import config


class CeleryConfig:
    """
    Centralized Celery configuration using class-based settings.
    Import this into your Celery app with:
        app.config_from_object('src.celery_config.CeleryConfig')
    """

    # --------------------------
    # Redis Settings
    # --------------------------
    broker_url = config.redis_url
    result_backend = config.redis_url

    # --------------------------
    # Serialization
    # --------------------------
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]

    timezone = "UTC"
    enable_utc = True

    # --------------------------
    # Queue Definitions
    # --------------------------
    task_default_queue = "default"
    task_queues = (
        Queue("default", routing_key="default"),
        
        Queue("fetch_user_id", routing_key="fetch_user_id"),
        
        Queue("fetch_user_bookmarks_task", routing_key="fetch_user_bookmarks"),
    )
    
    
    # --------------------------
    # Task Routing
    # --------------------------
    task_routes = {
        "src.celery.task.fetch_user_id_task": {"queue": "fetch_user_id"}, #beat schedule 
        
        "src.celery.task.fetch_write_bookmark_task": {"queue": "fetch_user_bookmarks"}
    }


    # --------------------------
    # Worker Behavior
    # --------------------------
    worker_prefetch_multiplier = 1
    task_acks_late = True
    worker_max_tasks_per_child = 1000

    # --------------------------
    # Retry Policy
    # --------------------------
    task_default_retry_delay = 60
    task_max_retries = 3

    # --------------------------
    # Beat (Scheduler) Settings
    # --------------------------
    beat_scheduler = "celery.beat.PersistentScheduler"
    beat_schedule_filename = "celerybeat-schedule"

    # --------------------------
    # Logging & Monitoring
    # --------------------------
    worker_hijack_root_logger = False
    worker_log_color = False
    worker_send_task_events = True
    task_send_sent_event = True



"""

# Start Redis (if using Docker)
docker run -d --name redis -p 6379:6379 redis:alpine

# Or install Redis locally
# Ubuntu: sudo apt-get install redis-server
# macOS: brew install redis

# Install required packages
pip install celery[redis] flower

# Start Celery worker (in one terminal)
celery -A src.celery.celery.bg_task worker -l info -Q fetch_user_id,fetch_user_bookmarks,default

-A src.celery.celery.bg_task → src/celery/celery.py file, bg_task is the Celery() instance you defined

worker → starts a worker

-l info → log level

-Q ... → tell this worker which queues to listen on


# Start Celery Beat scheduler (in another terminal)
celery -A src.celery.celery beat --loglevel=info



# Optional: Start Flower monitoring UI (in third terminal)
celery -A src.celery.celery flower --port=5555

# Production startup (single command)
celery -A src.services.celery_app worker --beat --loglevel=info --detach

# Check task status
celery -A src.services.celery_app inspect active

# Monitor with Flower
# Open browser to http://localhost:5555
"""
