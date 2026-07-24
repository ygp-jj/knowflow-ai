"""文档切片 ORM 模型定义。

字段与 scripts/neon-create-knowflow-tables.sql 中的 document_chunks 表保持一致。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentChunk(Base):
    """文档切片 ORM 模型，对应 document_chunks 表。"""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk_index"),
    )

    # 主键 ID，由数据库自增生成。
    id = Column(Integer, primary_key=True, index=True)
    # 所属文档 ID。
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    # 所属知识库 ID，便于按知识库检索切片。
    knowledge_base_id = Column(
        Integer,
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 切片在文档内的顺序，从 0 开始。
    chunk_index = Column(Integer, nullable=False)
    # 切片正文内容。
    content = Column(Text, nullable=False)
    # 内容哈希，用于排查与去重。
    content_hash = Column(String(64), nullable=False, index=True)
    # PDF 页码；非分页文档可为 NULL。
    page_number = Column(Integer, nullable=True)
    # Token 估算值（MVP 可用字符近似）。
    token_count = Column(Integer, nullable=False, default=0)
    # Milvus 向量 ID，第 3 阶段保持为空。
    vector_id = Column(String(128), nullable=True, index=True)
    # 扩展元数据，JSON 结构。
    chunk_metadata = Column("metadata", JSON, nullable=True)
    # 创建时间。
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
