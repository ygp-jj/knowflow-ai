"""文档切片写入与查询服务。"""

import hashlib

from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.token_service import estimate_token_count


def build_content_hash(content: str) -> str:
    """计算切片内容 SHA-256 十六进制摘要。"""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def replace_document_chunks(db: Session, document: Document, chunks: list[dict]) -> list[DocumentChunk]:
    """删除文档旧切片并写入新切片，同时更新 chunk_count。

    参数:
        db: 数据库会话。
        document: 目标文档 ORM 对象。
        chunks: ``[{content, page_number, chunk_index}, ...]``。
    """

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete(synchronize_session=False)

    created_chunks: list[DocumentChunk] = []
    for item in chunks:
        content = item["content"]
        chunk = DocumentChunk(
            document_id=document.id,
            knowledge_base_id=document.knowledge_base_id,
            chunk_index=item["chunk_index"],
            content=content,
            content_hash=build_content_hash(content),
            page_number=item.get("page_number"),
            token_count=estimate_token_count(content),
            vector_id=None,
            chunk_metadata=item.get("metadata"),
        )
        db.add(chunk)
        created_chunks.append(chunk)

    document.chunk_count = len(created_chunks)
    db.commit()

    for chunk in created_chunks:
        db.refresh(chunk)

    return created_chunks


def list_chunks(
    db: Session,
    document_id: int,
    page: int,
    page_size: int,
) -> tuple[list[DocumentChunk], int]:
    """按文档分页查询切片，按 chunk_index 升序。"""

    query = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id)
    total = query.count()
    items = (
        query.order_by(DocumentChunk.chunk_index.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def clear_document_chunks(db: Session, document_id: int) -> None:
    """删除指定文档的全部切片（不提交，由调用方控制事务）。"""

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)
