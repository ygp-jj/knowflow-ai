"""知识库 ORM 模型定义。

字段与 scripts/neon-create-knowflow-tables.sql 中的 knowledge_bases 表保持一致。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class KnowledgeBase(Base):
    """知识库 ORM 模型，对应 knowledge_bases 表。"""

    __tablename__ = "knowledge_bases"

    # 主键 ID，由数据库自增生成。
    id = Column(Integer, primary_key=True, index=True)
    # 知识库名称，创建和更新时必填。
    name = Column(String(200), nullable=False)
    # 知识库描述，可为空。
    description = Column(Text, nullable=True)
    # 所属用户 ID，由前端通过 API 参数传入。
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # 创建时间和更新时间由数据库默认值/更新逻辑维护。
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
