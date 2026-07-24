"""文档 ORM 模型定义。

字段与 scripts/neon-create-knowflow-tables.sql 中的 documents 表保持一致。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """文档 ORM 模型，对应 documents 表。"""

    __tablename__ = "documents"

    # 主键 ID，由数据库自增生成。
    id = Column(Integer, primary_key=True, index=True)
    # 所属知识库 ID，用于列表筛选和级联删除。
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    # 文档基础元数据，创建接口会从上传文件中填充。
    file_name = Column(String(255), nullable=False)
    # 业务文件类型存短扩展名（如 xlsx/pdf），不再存完整 MIME。
    file_type = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False)
    # 当前保持字符串状态，便于与 SQLite 测试环境兼容。
    status = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    # 创建时间和更新时间由数据库默认值和更新逻辑维护。
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
