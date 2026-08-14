"""文档管理请求与响应 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentUpdate(BaseModel):
    """更新文档请求。

    字段:
        id: 请求体传入的文档 ID。
        file_name: 更新后的文件名。
    """

    id: int = Field(..., gt=0, description="文档 ID")
    file_name: str = Field(..., min_length=1, max_length=255, description="文档文件名")


class DocumentRead(BaseModel):
    """文档响应数据。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    file_name: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str]
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentCreateRead(DocumentRead):
    """文档创建 / 触发切片 / 触发向量化响应，附带可选 Celery task_id。"""

    task_id: Optional[str] = None


class DocumentChunkRequest(BaseModel):
    """手动触发切片请求。

    字段:
        id: 文档 ID。
    """

    id: int = Field(..., gt=0, description="文档 ID")


class DocumentEmbedRequest(BaseModel):
    """手动触发向量化请求（第 4 阶段）。

    字段:
        id: 文档 ID；须已切片（chunked）或需重新向量化（embedded/failed）。
    """

    id: int = Field(..., gt=0, description="文档 ID")


class DocumentChunkRead(BaseModel):
    """文档切片响应数据。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    parent_chunk_id: Optional[int] = None
    chunk_index: int
    content: str
    page_number: Optional[int]
    token_count: int
