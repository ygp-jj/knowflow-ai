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


def get_knowledge_base(db: Session, knowledge_base_id: int) -> KnowledgeBase | None:
    """查询知识库是否存在（内部校验用，前端无需关心）。"""
    return db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()


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
) -> Document | None:
    """【前端上传文档时调用】上传文件到 MinIO 并创建文档记录。

    这是整个文档上传流程的入口，前端调用 /api/documents/upload 时，后端会调用此函数。

    工作流程（前端可见的步骤）：
        1. 检查知识库是否存在（不存在则返回 None）
        2. 构建对象存储路径（自动防重名）
        3. 上传文件到 MinIO
        4. 在数据库中创建文档记录，状态默认为 "uploaded"
        5. 提交事务，返回包含数据库生成字段（id、created_at 等）的文档对象

    返回的文档对象中，前端最关心的字段：
        - id: 文档唯一标识（后续查询、删除、触发切片都用它）
        - status: 当前状态（刚上传时为 "uploaded"）
        - file_name: 原始文件名
        - file_size: 文件大小（字节）
        - chunk_count: 切片数（初始为 0）

    注意：
        上传成功后，前端通常需要调用“触发切片”接口（start_document_chunking）
        才能真正完成文档的解析和切块。
    """
    if get_knowledge_base(db, knowledge_base_id) is None:
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
    knowledge_base_id: int | None
) -> tuple[list[Document], int]:
    """【前端查询文档列表】分页获取文档，可按知识库过滤。

    前端调用场景：
        - 知识库详情页展示文档列表
        - 全局文档管理页面

    返回顺序：
        按 id 降序（最新的文档排在最前面）

    返回值：
        - 第一项: 当前页的文档列表
        - 第二项: 总记录数（用于前端分页计算）

    前端展示建议：
        - 显示 status 字段，让用户知道文档当前是“待处理”还是“已切片”
        - 如果 status = "failed"，展示 error_message 字段（如有）
    """
    query = db.query(Document)
    if knowledge_base_id is not None:
        query = query.filter(Document.knowledge_base_id == knowledge_base_id)
    total = query.count()
    items = (
        query.order_by(Document.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_document(db: Session, document_id: int) -> Document | None:
    """【内部查询】按 ID 获取单个文档对象（前端不直接调用，由其他函数复用）。"""
    return db.query(Document).filter(Document.id == document_id).first()


def update_document(db: Session, payload: DocumentUpdate) -> Document | None:
    """【前端更新文档】修改文档的文件名。

    前端调用场景：用户重命名已上传的文档。

    注意：
        目前只支持更新 file_name，如需扩展其他字段，需同步修改 Schema。
    """
    document = get_document(db, payload.id)
    if document is None:
        return None

    document.file_name = payload.file_name
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, object_storage, document_id: int) -> bool:
    """【前端删除文档】删除文档记录、MinIO 文件，并尽力清理 Milvus 向量。

    工作流程：
        1. 查询文档是否存在
        2. best-effort 删除该文档在 Milvus 中的向量（失败只打日志，不阻断删除）
        3. 从 MinIO 删除原始文件
        4. 从数据库删除文档记录（切片通常由外键级联清理）

    前端调用后：
        文档及其切片会被移除；向量清理失败时可对照日志手动清 Milvus。
        返回 True 表示删除成功，False 表示文档不存在。
    """
    document = get_document(db, document_id)
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


def get_download_payload(db: Session, object_storage, document_id: int):
    """【前端下载文档】获取文件内容和文档元数据。

    前端调用场景：用户点击“下载”按钮时。

    返回值：
        - document: 文档元数据（包含文件名、文件类型等）
        - file_payload: MinIO 返回的文件内容（包含 bytes、content_type 等）

    如果文档不存在，两者都返回 None。
    """
    document = get_document(db, document_id)
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


def start_document_chunking(db: Session, document_id: int) -> tuple[Document | None, str | None, str | None]:
    """【前端手动触发切片】启动文档的异步解析 + 切片任务。

    这是前端在文档上传后，或者文档处理失败后，手动点击“开始切片”时调用的接口。

    返回值：
        - document: 文档对象（可能为 None，表示文档不存在）
        - task_id: Celery 任务 ID（可用于异步查询进度）
        - error_message: 错误描述（成功时为 None）

    前置校验（按顺序）：
        1. 文档是否存在
        2. 文档是否正在处理中（parsing / chunking / embedding）→ 拒绝重复触发
        3. 文档状态是否可切片（uploaded / failed / chunked / embedded）→ 不可切则返回错误

    前端调用后：
        - 如果 task_id 不为 None，文档状态会被 Celery 任务更新为 "parsing"
        - 前端点「刷新」观察 status 是否变为 "chunked" 或 "failed"（列表页不轮询）

    特别说明：
        - 即使文档已经是 "chunked"/"embedded"，也可以再次触发（重新切片/覆盖）
        - 重新切片后需再次点「向量化」才会更新 Milvus
        - 如果任务投递失败（如 Redis 不可用），会返回 error_message
    """
    document = get_document(db, document_id)
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


def start_document_embedding(db: Session, document_id: int) -> tuple[Document | None, str | None, str | None]:
    """【前端手动触发向量化】启动 Embedding + 写入 Milvus 的异步任务。

    状态预期：chunked/embedded/failed →（任务内）embedding → embedded | failed

    返回值：
        - document / task_id / error_message（与 start_document_chunking 同形）

    前置校验：
        1. 文档存在
        2. 非处理中
        3. 状态可向量化（chunked / embedded / failed）
        4. chunk_count > 0（没有切片无法 Embedding）
    """
    document = get_document(db, document_id)
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