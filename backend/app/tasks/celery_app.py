"""Celery 应用配置。"""

from celery import Celery

from app.core.config import settings

# KnowFlow 异步任务应用，broker/backend 均使用 Redis。
celery_app = Celery(
    "knowflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.document_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "app.tasks.document_tasks.process_document": {"queue": "documents"},
    },
)
