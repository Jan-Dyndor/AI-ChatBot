from celery import Celery

from backend.configuration.settings import get_settings

settings = get_settings()
celery_app = Celery(
    broker=settings.redis_broker,
    backend=settings.redis_backend,
    include=["backend.celery_app.celery_tasks"],
)


celery_app.conf.update(
    task_track_started=True,  # report a "STARTED" state, not just PENDING->SUCCESS
    task_time_limit=300,  # hard kill a task after 5 min
    result_expires=3600,  # drop results from Redis after 1 hour
)
