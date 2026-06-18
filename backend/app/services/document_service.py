"""文档管理业务服务。"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.schemas.document import DocumentUpdate


DEFAULT_DOCUMENT_STATUS = "uploaded"


def get_knowledge_base(db: Session, knowledge_base_id: int) -> KnowledgeBase | None:
    """查询知识库是否存在。"""

    return db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()


def build_object_name(knowledge_base_id: int, file_name: str) -> str:
    """构造 MinIO 对象名，避免文件名冲突。"""

    suffix = Path(file_name).suffix
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"knowledge-bases/{knowledge_base_id}/{timestamp}-{uuid4().hex}{suffix}"


def create_document(
    db: Session,
    object_storage,
    knowledge_base_id: int,
    file_name: str,
    file_type: str,
    file_bytes: bytes,
) -> Document | None:
    """上传文件并创建文档记录。"""

    if get_knowledge_base(db, knowledge_base_id) is None:
        return None

    object_name = build_object_name(knowledge_base_id, file_name)
    object_storage.upload_file(file_bytes, object_name, file_type)

    document = Document(
        knowledge_base_id=knowledge_base_id,
        file_name=file_name,
        file_type=file_type,
        file_path=object_name,
        file_size=len(file_bytes),
        status=DEFAULT_DOCUMENT_STATUS,
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, page: int, page_size: int, knowledge_base_id: int | None) -> tuple[list[Document], int]:
    """分页查询文档，可按知识库过滤。"""

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
    """按 ID 查询文档。"""

    return db.query(Document).filter(Document.id == document_id).first()


def update_document(db: Session, payload: DocumentUpdate) -> Document | None:
    """更新文档文件名。"""

    document = get_document(db, payload.id)
    if document is None:
        return None

    document.file_name = payload.file_name
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, object_storage, document_id: int) -> bool:
    """删除文档记录和对应对象。"""

    document = get_document(db, document_id)
    if document is None:
        return False

    object_storage.delete_file(document.file_path)
    db.delete(document)
    db.commit()
    return True


def get_download_payload(db: Session, object_storage, document_id: int):
    """获取下载所需的文件内容和文档元数据。"""

    document = get_document(db, document_id)
    if document is None:
        return None, None

    file_payload = object_storage.download_file(document.file_path)
    return document, file_payload
