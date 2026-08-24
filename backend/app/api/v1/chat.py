"""智能问答 HTTP 路由（无会话 ask / ask-stream + 5B 会话 CRUD 与 ask-stream）。

身份以 JWT 为准：owner/user 由 current_user 注入，前端不再传 user_id。
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatAskRequest,
    ChatAskRead,
    ChatMessageRead,
    ChatMessageReferenceRead,
    ChatSessionAskStreamRequest,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionUpdate,
)
from app.schemas.common import error_response, success_response
from app.services.chat_session_service import (
    ChatSessionServiceError,
    create_session,
    delete_session,
    get_references_by_message_ids,
    get_session,
    knowledge_base_name,
    list_messages,
    list_sessions,
    update_session_title,
)
from app.services.embedding_service import EmbeddingServiceError
from app.services.llm_service import LLMServiceError
from app.services.milvus_service import MilvusServiceError
from app.services.rag_service import (
    RagServiceError,
    SessionStreamGate,
    ask_knowledge_base,
    iter_ask_knowledge_base_events,
    iter_session_ask_events,
)

router = APIRouter()


def _format_sse(payload: dict) -> str:
    """把事件字典格式化为 SSE 文本帧。"""
    event_name = payload.get("event") or "message"
    data_obj = {key: value for key, value in payload.items() if key != "event"}
    data_text = json.dumps(data_obj, ensure_ascii=False)
    return f"event: {event_name}\ndata: {data_text}\n\n"


def _session_to_read(db: Session, session) -> ChatSessionRead:
    """ORM 会话转响应，附带知识库名称。"""
    data = ChatSessionRead.model_validate(session)
    data.knowledge_base_name = knowledge_base_name(db, session.knowledge_base_id)
    return data


# ---------- 无会话问答（5A / 调试） ----------


@router.post("/ask")
def ask(
    payload: ChatAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """单次知识库问答：完整 JSON（非流式兜底）。"""
    _ = current_user
    try:
        result: ChatAskRead = ask_knowledge_base(
            db,
            knowledge_base_id=payload.knowledge_base_id,
            question=payload.question,
        )
    except RagServiceError as exc:
        return error_response(exc.http_code, str(exc))
    except (EmbeddingServiceError, MilvusServiceError, LLMServiceError) as exc:
        return error_response(502, str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(500, f"问答失败: {exc}")

    return success_response(result.model_dump())


@router.post("/ask-stream")
def ask_stream(
    payload: ChatAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """无会话流式问答（SSE）。"""
    _ = current_user

    def event_generator() -> Iterator[str]:
        try:
            for item in iter_ask_knowledge_base_events(
                db,
                knowledge_base_id=payload.knowledge_base_id,
                question=payload.question,
            ):
                yield _format_sse(item)
        except RagServiceError as exc:
            yield _format_sse({"event": "error", "message": str(exc), "code": exc.http_code})
        except (EmbeddingServiceError, MilvusServiceError, LLMServiceError) as exc:
            yield _format_sse({"event": "error", "message": str(exc), "code": 502})
        except Exception as exc:  # noqa: BLE001
            yield _format_sse({"event": "error", "message": f"问答失败: {exc}", "code": 500})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- 会话 CRUD（5B） ----------


@router.post("/sessions/create")
def sessions_create(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建会话：绑定知识库，默认标题「新会话」。"""
    try:
        session = create_session(db, payload, user_id=current_user.id)
    except ChatSessionServiceError as exc:
        return error_response(exc.http_code, str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(500, f"创建会话失败: {exc}")
    return success_response(_session_to_read(db, session).model_dump())


@router.get("/sessions/list")
def sessions_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页列出会话。"""
    items, total = list_sessions(db, user_id=current_user.id, page=page, page_size=page_size)
    data = {
        "items": [_session_to_read(db, item).model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.get("/sessions/detail")
def sessions_detail(
    id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """会话详情。"""
    session = get_session(db, session_id=id, user_id=current_user.id)
    if session is None:
        return error_response(404, "会话不存在")
    return success_response(_session_to_read(db, session).model_dump())


@router.put("/sessions/update")
def sessions_update(
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动修改会话标题。"""
    session = update_session_title(db, payload, user_id=current_user.id)
    if session is None:
        return error_response(404, "会话不存在")
    return success_response(_session_to_read(db, session).model_dump())


@router.delete("/sessions/delete")
def sessions_delete(
    id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话（消息与引用 CASCADE）。"""
    ok = delete_session(db, session_id=id, user_id=current_user.id)
    if not ok:
        return error_response(404, "会话不存在")
    return success_response(None)


@router.get("/messages/list")
def messages_list(
    session_id: int = Query(..., gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页拉取会话消息（正序），assistant 带 references。"""
    try:
        items, total = list_messages(
            db,
            session_id=session_id,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
        )
    except ChatSessionServiceError as exc:
        return error_response(exc.http_code, str(exc))

    refs_map = get_references_by_message_ids(db, [m.id for m in items])
    read_items = []
    for msg in items:
        row = ChatMessageRead.model_validate(msg)
        row.references = [
            ChatMessageReferenceRead.model_validate(ref) for ref in refs_map.get(msg.id, [])
        ]
        read_items.append(row.model_dump())

    return success_response(
        {
            "items": read_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/sessions/ask-stream")
async def sessions_ask_stream(
    request: Request,
    payload: ChatSessionAskStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """会话内流式提问（产品主路径）。

    注意：前端 Abort 停止生成时，已落库的 user 保留，assistant 不会写入。
    """
    persist_gate = SessionStreamGate()
    user_id = current_user.id

    async def event_generator():
        gen = iter_session_ask_events(
            db,
            session_id=payload.session_id,
            user_id=user_id,
            question=payload.question,
            persist_gate=persist_gate,
        )
        try:
            while True:
                if await request.is_disconnected():
                    persist_gate.abort()
                    gen.close()
                    break
                try:
                    item = next(gen)
                except StopIteration:
                    break
                yield _format_sse(item)
                if await request.is_disconnected():
                    persist_gate.abort()
                    gen.close()
                    break
        except GeneratorExit:
            persist_gate.abort()
            gen.close()
            raise
        except RagServiceError as exc:
            yield _format_sse({"event": "error", "message": str(exc), "code": exc.http_code})
        except ChatSessionServiceError as exc:
            yield _format_sse({"event": "error", "message": str(exc), "code": exc.http_code})
        except (EmbeddingServiceError, MilvusServiceError, LLMServiceError) as exc:
            yield _format_sse({"event": "error", "message": str(exc), "code": 502})
        except Exception as exc:  # noqa: BLE001
            yield _format_sse({"event": "error", "message": f"会话问答失败: {exc}", "code": 500})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
