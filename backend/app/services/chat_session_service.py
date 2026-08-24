"""聊天会话 CRUD 与消息查询。

约定（5B + 登录鉴权）：
- user_id 由 JWT 当前用户注入，前端不再传入
- 删除会话依赖 DB CASCADE，同时清掉消息与引用
- 默认标题「新会话」；仅该默认值可被首条用户问题自动覆盖
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatReference, ChatSession
from app.models.knowledge_base import KnowledgeBase
from app.schemas.chat import (
    DEFAULT_SESSION_TITLE,
    SESSION_TITLE_MAX_LEN,
    ChatSessionCreate,
    ChatSessionUpdate,
)


class ChatSessionServiceError(RuntimeError):
    """会话业务可预期错误。"""

    def __init__(self, message: str, *, http_code: int = 400) -> None:
        super().__init__(message)
        self.http_code = http_code


def _truncate_title(text: str) -> str:
    """截断标题到 SESSION_TITLE_MAX_LEN。"""
    cleaned = (text or "").strip().replace("\n", " ")
    if len(cleaned) <= SESSION_TITLE_MAX_LEN:
        return cleaned
    return cleaned[:SESSION_TITLE_MAX_LEN] + "…"


def create_session(db: Session, payload: ChatSessionCreate, *, user_id: int) -> ChatSession:
    """创建会话并绑定知识库。

    参数:
        db: 数据库会话。
        payload: 创建参数。
        user_id: 当前登录用户 ID。
    返回:
        已落库的 ChatSession。
    """
    kb = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id == payload.knowledge_base_id, KnowledgeBase.owner_id == user_id)
        .first()
    )
    if kb is None:
        raise ChatSessionServiceError("知识库不存在", http_code=404)

    title = (payload.title or "").strip() or DEFAULT_SESSION_TITLE
    title = _truncate_title(title)

    session = ChatSession(
        knowledge_base_id=payload.knowledge_base_id,
        user_id=user_id,
        title=title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(
    db: Session,
    *,
    user_id: int,
    page: int,
    page_size: int,
) -> tuple[list[ChatSession], int]:
    """分页列出某用户的会话（按更新时间倒序）。"""
    query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
    total = query.count()
    items = (
        query.order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_session(db: Session, *, session_id: int, user_id: int) -> ChatSession | None:
    """按 id + user_id 取会话。"""
    return (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )


def update_session_title(
    db: Session,
    payload: ChatSessionUpdate,
    *,
    user_id: int,
) -> ChatSession | None:
    """手动改会话标题。"""
    session = get_session(db, session_id=payload.id, user_id=user_id)
    if session is None:
        return None
    session.title = _truncate_title(payload.title)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, *, session_id: int, user_id: int) -> bool:
    """删除会话；消息与引用由 FK CASCADE 清理。返回是否删到了记录。"""
    session = get_session(db, session_id=session_id, user_id=user_id)
    if session is None:
        return False
    db.delete(session)
    db.commit()
    return True


def maybe_auto_update_title(db: Session, session: ChatSession, question: str) -> None:
    """首条用户问题时：若仍是默认「新会话」，则用问题截断覆盖 title。"""
    if session.title != DEFAULT_SESSION_TITLE:
        return
    session.title = _truncate_title(question)
    db.add(session)
    db.commit()
    db.refresh(session)


def add_message(
    db: Session,
    *,
    session_id: int,
    role: str,
    content: str,
) -> ChatMessage:
    """写入一条消息；token_count 按字符数粗算。"""
    text = content or ""
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=text,
        token_count=len(text),
    )
    db.add(message)
    # 顺带 bump 会话 updated_at（依赖 onupdate；显式 touch 更稳）
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is not None:
        db.add(session)
    db.commit()
    db.refresh(message)
    return message


def add_references_for_message(
    db: Session,
    *,
    message_id: int,
    references: list,
) -> None:
    """把检索引用落到 chat_references（references 为 ChatReference schema 或兼容对象）。"""
    for item in references:
        score = getattr(item, "score", None)
        if score is None and isinstance(item, dict):
            score = item.get("score")
        preview = getattr(item, "content", None)
        if preview is None and isinstance(item, dict):
            preview = item.get("content") or item.get("content_preview")
        document_id = getattr(item, "document_id", None)
        if document_id is None and isinstance(item, dict):
            document_id = item.get("document_id")
        chunk_id = getattr(item, "chunk_id", None)
        if chunk_id is None and isinstance(item, dict):
            chunk_id = item.get("chunk_id")

        db.add(
            ChatReference(
                message_id=message_id,
                document_id=int(document_id),
                chunk_id=int(chunk_id),
                score=float(score if score is not None else 0.0),
                content_preview=(preview or "")[:2000],
                page_number=None,
            )
        )
    db.commit()


def list_messages(
    db: Session,
    *,
    session_id: int,
    user_id: int,
    page: int,
    page_size: int,
) -> tuple[list[ChatMessage], int]:
    """分页拉取会话消息（正序，便于聊天展示）；校验会话归属。"""
    session = get_session(db, session_id=session_id, user_id=user_id)
    if session is None:
        raise ChatSessionServiceError("会话不存在", http_code=404)

    query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    total = query.count()
    items = (
        query.order_by(ChatMessage.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_references_by_message_ids(
    db: Session,
    message_ids: list[int],
) -> dict[int, list[ChatReference]]:
    """批量查引用，按 message_id 分组。"""
    if not message_ids:
        return {}
    rows = (
        db.query(ChatReference)
        .filter(ChatReference.message_id.in_(message_ids))
        .order_by(ChatReference.id.asc())
        .all()
    )
    grouped: dict[int, list[ChatReference]] = {mid: [] for mid in message_ids}
    for row in rows:
        grouped.setdefault(row.message_id, []).append(row)
    return grouped


def load_recent_messages(
    db: Session,
    *,
    session_id: int,
    limit: int,
) -> list[ChatMessage]:
    """取最近 limit 条消息，再按时间正序返回（喂 LLM 用）。"""
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return rows


def truncate_history_by_chars(
    messages: list[ChatMessage],
    max_chars: int,
) -> list[ChatMessage]:
    """从更早的消息开始丢弃，使 content 总长不超过 max_chars。

    至少保留最后一条（通常是本轮 user），避免历史被砍光后丢了当前问题。
    """
    if max_chars <= 0 or not messages:
        return messages

    kept: list[ChatMessage] = []
    used = 0
    # 从新到旧累加，再反转回正序
    for msg in reversed(messages):
        length = len(msg.content or "")
        if kept and used + length > max_chars:
            break
        kept.append(msg)
        used += length
    kept.reverse()
    return kept


def knowledge_base_name(db: Session, knowledge_base_id: int) -> str | None:
    """查知识库名称，供会话 Read 附带。"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    return kb.name if kb is not None else None
