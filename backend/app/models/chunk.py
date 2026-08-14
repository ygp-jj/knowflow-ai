"""文档切片 ORM 模型定义。

这是数据库表 document_chunks 对应的 Python 模型。
每个 DocumentChunk 对象代表文档被切分后的一个【文本片段（Chunk）】。
前端通过文档详情页看到的“分块内容”，就是查询这张表得到的。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentChunk(Base):
    """文档切片 ORM 模型，对应 document_chunks 表。

    这张表的核心职责：存储每个文档被切分后的所有小块。
    前端展示、检索、高亮段落时，操作的数据基本都来自这张表。
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        # 联合唯一约束：同一个文档内，chunk_index 不能重复。
        # 即文档 1 的 chunk 编号 0,1,2,3... 是严格连续的。
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk_index"),
    )

    # ------------------------------------------------
    # 主键与关联字段（前端一般不用关心 id 本身，更多用作查询条件）
    # ------------------------------------------------

    # 主键 ID，由数据库自增生成。
    # 前端几乎不会用到这个 id，它主要用于后端关联和索引。
    id = Column(Integer, primary_key=True, index=True)

    # 所属文档 ID（外键，指向 documents 表）。
    # 前端查询某个文档的切片时，用这个字段过滤。
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # 所属知识库 ID（外键，指向 knowledge_bases 表）。
    # 冗余存储，方便按知识库批量查询切片（如“检索整个知识库”时使用）。
    knowledge_base_id = Column(
        Integer,
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 父切片 ID（自关联）。大标题（章/条等）为 NULL；子块指向所属父标题块。
    # 检索命中父块后，可按此字段继续拉取子块正文。
    parent_chunk_id = Column(
        Integer,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------
    # 切片内容字段（前端最关心的数据）
    # ------------------------------------------------

    # 切片在文档内的顺序，从 0 开始。
    # 前端按此字段排序显示，就能还原文档的原文顺序。
    chunk_index = Column(Integer, nullable=False)

    # 切片正文内容（纯文本，Markdown 或 HTML 在生成时已被剥离）。
    # 这是前端展示的核心字段，渲染时需要注意转义（默认已无富文本）。
    content = Column(Text, nullable=False)

    # 内容哈希（SHA-256），用于后端去重或检查内容是否变更。
    # 前端不需要展示，也不需要通过 API 返回给前端。
    content_hash = Column(String(64), nullable=False, index=True)

    # PDF 页码（仅对 PDF 文档有效，Word/TXT 文档为 NULL）。
    # 前端如果需要标注来源页码，就用这个字段。
    page_number = Column(Integer, nullable=True)

    # Token 估算值（用于控制送入 AI 的 Token 总量）。
    # 前端展示时，可显示“本块约 X tokens”，帮助用户了解上下文长度。
    token_count = Column(Integer, nullable=False, default=0)

    # Milvus 向量 ID（用于向量检索）。
    # 第 3 阶段（向量化）之前，这个字段为 NULL。
    # 前端如果做语义检索，会通过后端接口拿到对应的 chunk，而不直接操作这个 ID。
    vector_id = Column(String(128), nullable=True, index=True)

    # 扩展元数据（JSON 结构），可存放额外信息如：
    # - 来源 URL
    # - 标签
    # - 自定义属性
    # 前端如果需要展示额外信息，后端会解析后返回到 API 响应中。
    chunk_metadata = Column("metadata", JSON, nullable=True)

    # 创建时间（数据库自动生成，不可手动修改）。
    # 前端一般不需要展示，更多用于后台审计或排查问题。
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)