"""智能问答请求与响应 Schema。"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    """单次问答请求（无会话）。

    字段:
        knowledge_base_id: 要检索的知识库 ID。
        question: 用户问题。
    """

    knowledge_base_id: int = Field(..., gt=0, description="知识库 ID")
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")


class ChatReference(BaseModel):
    """答案引用的切片信息。"""

    chunk_id: int
    document_id: int
    chunk_index: int
    score: Optional[float] = None
    content: str


class ChatAskRead(BaseModel):
    """单次问答响应。"""

    answer: str
    question: str
    knowledge_base_id: int
    references: list[ChatReference] = Field(default_factory=list)
