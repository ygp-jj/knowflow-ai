"""智能问答 / 会话相关请求与响应 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatAskRequest(BaseModel):
    """单次问答请求（无会话）。

    字段:
        knowledge_base_id: 要检索的知识库 ID。
        question: 用户问题。
    """

    knowledge_base_id: int = Field(..., gt=0, description="知识库 ID")
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")


class ChatReference(BaseModel):
    """答案引用的切片信息（接口层；落库时映射到 content_preview）。"""

    chunk_id: int
    document_id: int
    chunk_index: int = 0
    score: Optional[float] = None
    content: str


class ChatAskRead(BaseModel):
    """单次问答响应。"""

    answer: str
    question: str
    knowledge_base_id: int
    references: list[ChatReference] = Field(default_factory=list)


# ---------- 会话 CRUD ----------

# 创建会话时的默认标题；仅当 title 仍等于该值时，首条用户问题才会自动覆盖。
DEFAULT_SESSION_TITLE = "新会话"
# 自动/手动标题最大长度（截断用）。
SESSION_TITLE_MAX_LEN = 50


class ChatSessionCreate(BaseModel):
    """创建会话请求。"""

    user_id: int = Field(..., gt=0, description="用户 ID（联调阶段前端显式传入）")
    knowledge_base_id: int = Field(..., gt=0, description="绑定的知识库 ID，会话内不可改")
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="可选标题；缺省为「新会话」",
    )


class ChatSessionUpdate(BaseModel):
    """更新会话标题（手动改名）。"""

    id: int = Field(..., gt=0, description="会话 ID")
    user_id: int = Field(..., gt=0, description="用户 ID，用于归属校验")
    title: str = Field(..., min_length=1, max_length=255, description="新标题")


class ChatSessionRead(BaseModel):
    """会话详情 / 列表项。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    # 列表/详情可选附带知识库名称，方便前端右侧展示（服务层填充）。
    knowledge_base_name: Optional[str] = None


class ChatSessionAskStreamRequest(BaseModel):
    """会话内流式提问请求。知识库取自会话，不在此重复传。"""

    session_id: int = Field(..., gt=0, description="会话 ID")
    user_id: int = Field(..., gt=0, description="用户 ID")
    question: str = Field(..., min_length=1, max_length=2000, description="本轮问题")


class ChatMessageReferenceRead(BaseModel):
    """消息列表里挂在 assistant 上的引用。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    chunk_id: int
    score: float
    content_preview: str
    page_number: Optional[int] = None


class ChatMessageRead(BaseModel):
    """消息列表项。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    token_count: int
    created_at: datetime
    references: list[ChatMessageReferenceRead] = Field(default_factory=list)
