"""知识库管理请求和响应 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求。

    字段:
        name: 知识库名称，不能为空，最大 200 字符。
        description: 知识库描述，可为空。
    说明:
        owner_id 由服务端从 JWT 注入，不再由前端传入。
    """

    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(default=None, description="知识库描述")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求。

    字段:
        id: 请求体传入的知识库 ID。
        name: 更新后的知识库名称。
        description: 更新后的知识库描述，可为空。
    说明:
        归属校验用 JWT 当前用户 id，不再传 owner_id。
    """

    id: int = Field(..., gt=0, description="知识库 ID")
    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(default=None, description="知识库描述")


class KnowledgeBaseRead(BaseModel):
    """知识库响应数据。

    字段:
        id: 知识库 ID。
        name: 知识库名称。
        description: 知识库描述。
        owner_id: 所属用户 ID（响应中仍返回，便于展示）。
        created_at: 创建时间。
        updated_at: 更新时间。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime
