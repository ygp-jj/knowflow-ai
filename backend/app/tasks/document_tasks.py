"""文档解析与切片 Celery 任务。

   这是一个【异步后台任务】。
   当前端上传文档后，后端会把这个任务扔给 Celery 队列执行，
   前端通过轮询文档状态（/api/documents/{id}/status）来感知处理进度。
"""

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

# ---------------------- 状态常量（前端轮询时看到的字段值） ----------------------
STATUS_PARSING = "parsing"      # 下载中 / 解析中
STATUS_CHUNKING = "chunking"    # 切片中（AI/规则拆分文本块）
STATUS_CHUNKED = "chunked"      # 已完成（可查看/检索状态）
STATUS_FAILED = "failed"        # 失败（查看 error_message 字段获取原因）


def _update_document_status(db, document, status: str, error_message: str | None = None) -> None:
    """工具函数：更新文档状态并提交到数据库。

       前端关心的字段：
         - document.status: 当前进度 (parsing -> chunking -> chunked / failed)
         - document.error_message: 失败时的具体报错原因
    """
    document.status = status
    document.error_message = error_message
    db.commit()
    db.refresh(document)


def _download_to_temp_file(object_storage, object_name: str, file_name: str) -> str:
    """从对象存储（如 MinIO / OSS）下载文件到本地临时目录。

       原因：解析库通常只能读取本地文件路径，不能直接读流。
       下载完成后返回本地临时文件路径。
    """
    payload = object_storage.download_file(object_name)
    if payload is None:
        # 这里的报错会体现在前端看到的 error_message 中
        raise FileNotFoundError(f"对象存储中不存在文件: {object_name}")

    # 保留原文件后缀（如 .pdf / .docx），帮助解析库识别格式
    suffix = Path(file_name).suffix or ".bin"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        temp_file.write(payload["bytes"])
        temp_file.flush()
        return temp_file.name
    finally:
        temp_file.close()


def run_process_document(document_id: int, object_storage=None) -> dict:
    """同步执行文档解析切片主流程（非异步版本，用于单测或调试）。

       这个函数内部包含了【完整的状态流转】，前端无需感知内部细节，
       只需关注返回的 status 字段和轮询数据库中的文档状态。
    """
    db = SessionLocal()
    temp_path = None

    try:
        # 1. 检查文档是否存在
        document = get_document(db, document_id)
        if document is None:
            return {"document_id": document_id, "status": STATUS_FAILED, "error": "文档不存在"}

        storage = object_storage or get_object_storage()

        # 2. 状态流转：开始下载解析
        _update_document_status(db, document, STATUS_PARSING)

        # 3. 下载文件到本地（这一步若失败，前端看到 failed + 具体报错）
        temp_path = _download_to_temp_file(storage, document.file_path, document.file_name)

        # 4. 核心解析：根据文件类型（PDF/Word/TXT）提取文字内容
        pages = parse_document(temp_path)

        # 5. 状态流转：开始文本切片（把大段文字切成小段，便于 AI 检索）
        _update_document_status(db, document, STATUS_CHUNKING)
        chunks = split_text(pages)  # 调用切分算法（按段落/按长度/按语义）

        # 如果没有切出任何文本块，视为无效文档
        if not chunks:
            raise ValueError("文档无有效文本，无法切片")

        # 6. 数据落库：删掉旧切片，写入新切片（即分块结果）
        replace_document_chunks(db, document, chunks)

        # 7. 状态流转：完成
        _update_document_status(db, document, STATUS_CHUNKED, error_message=None)

        # 8. 返回结果（chunk_count 可供前端展示“已分块数量”）
        return {
            "document_id": document_id,
            "status": STATUS_CHUNKED,
            "chunk_count": document.chunk_count,
        }

    except Exception as exc:  # noqa: BLE001
        # 【重要】任何异常（网络超时、文件格式不支持、磁盘不足）都会被捕获，
        # 并写入数据库，前端通过状态接口可看到具体的 error_message。
        if "document" in locals() and document is not None:
            message = str(exc)
            if isinstance(exc, UnsupportedDocumentTypeError):
                # 例如：“不支持 .ppt 格式，目前仅支持 PDF、Word、TXT”
                message = str(exc)
            _update_document_status(db, document, STATUS_FAILED, error_message=message)
        return {
            "document_id": document_id,
            "status": STATUS_FAILED,
            "error": str(exc),
        }

    finally:
        # 清理临时文件（防止磁盘被占满）
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        db.close()


@celery_app.task(name="app.tasks.document_tasks.process_document")
def process_document(document_id: int) -> dict:
    """【前端调用的异步任务入口】

       前端上传文档后，后端通常这样调用：
       process_document.delay(document_id)

       前端接下来应该：
       1. 每隔 2-3 秒 GET /api/documents/{document_id}
       2. 观察返回的 status 字段：
          - "parsing"   => 等待
          - "chunking"  => 等待
          - "chunked"   => 成功，可以查看/检索了
          - "failed"    => 失败，读取 error_message 并展示给用户
    """
    return run_process_document(document_id)