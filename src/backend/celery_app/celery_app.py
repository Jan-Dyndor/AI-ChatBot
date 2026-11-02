from pathlib import Path

from celery import Celery

from backend.configuration.settings import get_settings


def create_celery_app(env_file: Path | None = None):
    settings = get_settings(env_file)
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
    return celery_app


celery_app = create_celery_app()
