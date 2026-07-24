"""文档解析与切片 Celery 任务。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.core.database import SessionLocal
from app.services.chunk_service import replace_document_chunks
from app.services.document_parser import UnsupportedDocumentTypeError, parse_document
from app.services.document_service import get_document
from app.services.object_storage import get_object_storage
from app.services.text_splitter import split_pages_to_chunks
from app.tasks.celery_app import celery_app


STATUS_PARSING = "parsing"
STATUS_CHUNKING = "chunking"
STATUS_CHUNKED = "chunked"
STATUS_FAILED = "failed"


def _update_document_status(db, document, status: str, error_message: str | None = None) -> None:
    """更新文档状态与错误信息并提交。"""

    document.status = status
    document.error_message = error_message
    db.commit()
    db.refresh(document)


def _download_to_temp_file(object_storage, object_name: str, file_name: str) -> str:
    """从对象存储下载文件到本地临时路径，返回绝对路径。"""

    payload = object_storage.download_file(object_name)
    if payload is None:
        raise FileNotFoundError(f"对象存储中不存在文件: {object_name}")

    suffix = Path(file_name).suffix or ".bin"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        temp_file.write(payload["bytes"])
        temp_file.flush()
        return temp_file.name
    finally:
        temp_file.close()


def run_process_document(document_id: int, object_storage=None) -> dict:
    """同步执行文档解析切片主流程，便于单测直接调用。

    参数:
        document_id: 文档 ID。
        object_storage: 可选对象存储；默认使用真实 MinIO 客户端。
    """

    db = SessionLocal()
    temp_path = None

    try:
        document = get_document(db, document_id)
        if document is None:
            return {"document_id": document_id, "status": STATUS_FAILED, "error": "文档不存在"}

        storage = object_storage or get_object_storage()
        _update_document_status(db, document, STATUS_PARSING)

        temp_path = _download_to_temp_file(storage, document.file_path, document.file_name)
        pages = parse_document(temp_path)

        _update_document_status(db, document, STATUS_CHUNKING)
        chunks = split_pages_to_chunks(pages)
        if not chunks:
            raise ValueError("文档无有效文本，无法切片")

        replace_document_chunks(db, document, chunks)
        _update_document_status(db, document, STATUS_CHUNKED, error_message=None)

        return {
            "document_id": document_id,
            "status": STATUS_CHUNKED,
            "chunk_count": document.chunk_count,
        }
    except Exception as exc:  # noqa: BLE001 - 任务边界需捕获全部异常并落库
        if "document" in locals() and document is not None:
            message = str(exc)
            if isinstance(exc, UnsupportedDocumentTypeError):
                message = str(exc)
            _update_document_status(db, document, STATUS_FAILED, error_message=message)
        return {
            "document_id": document_id,
            "status": STATUS_FAILED,
            "error": str(exc),
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        db.close()


@celery_app.task(name="app.tasks.document_tasks.process_document")
def process_document(document_id: int) -> dict:
    """Celery 任务入口：解析文档并写入切片，成功状态为 chunked。"""

    return run_process_document(document_id)
