"""文档管理业务服务。

   这是前端上传、管理文档时，后端最直接调用的服务层。
   它负责：
        - 接收上传的文件，存入对象存储（MinIO），并创建文档记录
        - 查询文档列表（支持按知识库筛选和分页）
        - 更新文档信息（如文件名）
        - 删除文档（连同对象存储、Milvus 向量一起清理）
        - 提供下载所需的内容
        - 手动触发文档的异步切片 / 向量化任务
   前端通过 REST API 调用这些功能；列表页不轮询，用户点「刷新」查看 status。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.schemas.document import DocumentUpdate

logger = logging.getLogger(__name__)


# 文档刚上传后的初始状态（前端上传成功后看到的状态）
DEFAULT_DOCUMENT_STATUS = "uploaded"


def get_knowledge_base(
    db: Session,
    knowledge_base_id: int,
    *,
    owner_id: int | None = None,
) -> KnowledgeBase | None:
    """查询知识库是否存在；传入 owner_id 时校验归属。"""
    query = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id)
    if owner_id is not None:
        query = query.filter(KnowledgeBase.owner_id == owner_id)
    return query.first()


def build_object_name(knowledge_base_id: int, file_name: str) -> str:
    """构造 MinIO 对象名（存储路径），避免文件名冲突。

    规则：knowledge-bases/{知识库ID}/{时间戳}-{随机UUID}.{扩展名}
    例如：knowledge-bases/3/20260724123045-a1b2c3d4e5f6.pdf

    前端无需关心这个字段，它只在后端内部使用。
    """
    suffix = Path(file_name).suffix
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"knowledge-bases/{knowledge_base_id}/{timestamp}-{uuid4().hex}{suffix}"


def resolve_file_type(file_name: str, content_type: str | None = None) -> str:
    """从文件名提取扩展名作为业务文件类型（如 'pdf'、'docx'）。

    前端可见的文档列表中的 file_type 字段就来自这里。
    如果文件名没有扩展名，则回退到 content_type（MIME 类型）。
    """
    extension = Path(file_name).suffix.lstrip(".").lower()
    if extension:
        return extension
    if content_type:
        return content_type
    return "bin"


def create_document(
    db: Session,
    object_storage,
    knowledge_base_id: int,
    file_name: str,
    file_bytes: bytes,
    content_type: str | None = None,
    *,
    owner_id: int,
) -> Document | None:
    """【前端上传文档时调用】上传文件到 MinIO 并创建文档记录。

    仅允许上传到当前用户拥有的知识库。
    """
    if get_knowledge_base(db, knowledge_base_id, owner_id=owner_id) is None:
        return None

    object_content_type = content_type or "application/octet-stream"
    file_type = resolve_file_type(file_name, object_content_type)
    object_name = build_object_name(knowledge_base_id, file_name)
    object_storage.upload_file(file_bytes, object_name, object_content_type)

    document = Document(
        knowledge_base_id=knowledge_base_id,
        file_name=file_name,
        file_type=file_type,          # 扩展名（如 pdf）
        file_path=object_name,        # MinIO 存储路径
        file_size=len(file_bytes),
        status=DEFAULT_DOCUMENT_STATUS,  # "uploaded"
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(
    db: Session,
    page: int,
    page_size: int,
    knowledge_base_id: int | None,
    *,
    owner_id: int,
) -> tuple[list[Document], int]:
    """【前端查询文档列表】分页获取**当前用户**知识库下的文档。

    前端调用场景：
        - 知识库详情页展示文档列表
        - 全局文档管理页面

    返回顺序：
        按 id 降序（最新的文档排在最前面）
    """
    query = (
        db.query(Document)
        .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
        .filter(KnowledgeBase.owner_id == owner_id)
    )
    if knowledge_base_id is not None:
        # 同时校验该知识库属于当前用户（join 已限制 owner）
        query = query.filter(Document.knowledge_base_id == knowledge_base_id)
    total = query.count()
    items = (
        query.order_by(Document.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_document(
    db: Session,
    document_id: int,
    *,
    owner_id: int | None = None,
) -> Document | None:
    """按 ID 获取文档；传入 owner_id 时仅返回归属当前用户知识库的文档。"""
    query = db.query(Document).filter(Document.id == document_id)
    if owner_id is not None:
        query = query.join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id).filter(
            KnowledgeBase.owner_id == owner_id
        )
    return query.first()


def update_document(
    db: Session,
    payload: DocumentUpdate,
    *,
    owner_id: int,
) -> Document | None:
    """【前端更新文档】修改文档的文件名（仅本人知识库下的文档）。"""
    document = get_document(db, payload.id, owner_id=owner_id)
    if document is None:
        return None

    document.file_name = payload.file_name
    db.commit()
    db.refresh(document)
    return document


def delete_document(
    db: Session,
    object_storage,
    document_id: int,
    *,
    owner_id: int,
) -> bool:
    """【前端删除文档】删除本人知识库下的文档记录、MinIO 文件，并尽力清理 Milvus。"""
    document = get_document(db, document_id, owner_id=owner_id)
    if document is None:
        return False

    # 向量清理失败不应挡住业务删除；否则 Milvus 宕机会导致文档无法删
    try:
        from app.services.milvus_service import get_milvus_service

        get_milvus_service().delete_by_document_id(document_id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "删除文档时清理 Milvus 失败（已忽略）: document_id=%s",
            document_id,
        )

    object_storage.delete_file(document.file_path)
    db.delete(document)
    db.commit()
    return True


def get_download_payload(
    db: Session,
    object_storage,
    document_id: int,
    *,
    owner_id: int,
):
    """【前端下载文档】获取本人知识库下文档的文件内容与元数据。"""
    document = get_document(db, document_id, owner_id=owner_id)
    if document is None:
        return None, None

    file_payload = object_storage.download_file(document.file_path)
    return document, file_payload


def enqueue_document_processing(document_id: int) -> str | None:
    """【内部工具】将文档解析切片任务投递到 Celery 队列。

    返回：
        - 成功时：Celery 任务的 task_id（可用来查询任务状态）
        - 失败时：None（通常是因为 Redis 不可用）

    前端不需要直接调用这个函数，而是通过 start_document_chunking。
    """
    try:
        from app.tasks.document_tasks import process_document

        async_result = process_document.delay(document_id)
        return async_result.id
    except Exception:
        return None


# 允许手动触发切片的状态（前端点击“切片”按钮时的可执行条件）
CHUNKABLE_STATUSES = {"uploaded", "failed", "chunked", "embedded"}
# 允许手动触发向量化的状态（需已有切片；failed 用于 Embedding/Milvus 失败后重试）
EMBEDDABLE_STATUSES = {"chunked", "embedded", "failed"}
# 正在处理中的状态（禁止重复触发切片或向量化）
PROCESSING_STATUSES = {"parsing", "chunking", "embedding"}


def start_document_chunking(
    db: Session,
    document_id: int,
    *,
    owner_id: int,
) -> tuple[Document | None, str | None, str | None]:
    """【前端手动触发切片】启动文档的异步解析 + 切片任务（仅本人知识库）。"""
    document = get_document(db, document_id, owner_id=owner_id)
    if document is None:
        return None, None, "文档不存在"

    if document.status in PROCESSING_STATUSES:
        return document, None, "文档正在处理中，请稍后再试"

    if document.status not in CHUNKABLE_STATUSES:
        return document, None, f"当前状态「{document.status}」不可切片"

    task_id = enqueue_document_processing(document.id)
    if task_id is None:
        return document, None, "切片任务投递失败，请检查 Redis 与 Celery Worker"

    return document, task_id, None


def enqueue_document_embedding(document_id: int) -> str | None:
    """【内部工具】将文档向量化任务投递到 Celery 队列。

    返回:
        成功时为 Celery task_id；失败（如 Redis 不可用）为 None。
    """
    try:
        from app.tasks.embedding_tasks import embed_document

        async_result = embed_document.delay(document_id)
        return async_result.id
    except Exception:  # noqa: BLE001
        return None


def start_document_embedding(
    db: Session,
    document_id: int,
    *,
    owner_id: int,
) -> tuple[Document | None, str | None, str | None]:
    """【前端手动触发向量化】启动 Embedding + 写入 Milvus（仅本人知识库）。"""
    document = get_document(db, document_id, owner_id=owner_id)
    if document is None:
        return None, None, "文档不存在"

    if document.status in PROCESSING_STATUSES:
        return document, None, "文档正在处理中，请稍后再试"

    if document.status not in EMBEDDABLE_STATUSES:
        return document, None, f"当前状态「{document.status}」不可向量化，请先完成切片"

    if int(document.chunk_count or 0) <= 0:
        return document, None, "文档没有切片，请先完成切片后再向量化"

    task_id = enqueue_document_embedding(document.id)
    if task_id is None:
        return document, None, "向量化任务投递失败，请检查 Redis 与 Celery Worker"

    return document, task_id, None
