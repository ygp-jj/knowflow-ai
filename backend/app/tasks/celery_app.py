"""Celery 应用配置。"""

import sys

from celery import Celery

from app.core.config import settings

# KnowFlow 异步任务应用，broker/backend 均使用 Redis。
celery_app = Celery(
    "knowflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    # 切片 + 向量化任务均需被 Worker 加载；漏掉 include 会导致「收到任务却找不到」
    include=[
        "app.tasks.document_tasks",
        "app.tasks.embedding_tasks",
    ],
)

# Windows 不支持 prefork 进程池，默认改用 solo，避免 PermissionError / 句柄无效。
_worker_pool = "solo" if sys.platform.startswith("win") else "prefork"

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_pool=_worker_pool,
    task_routes={
        "app.tasks.document_tasks.process_document": {"queue": "documents"},
        "app.tasks.embedding_tasks.embed_document": {"queue": "documents"},
    },
)
