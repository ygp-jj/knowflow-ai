"""智能问答 HTTP 路由（非流式 /ask + 流式 /ask-stream）。"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatAskRequest, ChatAskRead
from app.schemas.common import error_response, success_response
from app.services.embedding_service import EmbeddingServiceError
from app.services.llm_service import LLMServiceError
from app.services.milvus_service import MilvusServiceError
from app.services.rag_service import (
    RagServiceError,
    ask_knowledge_base,
    iter_ask_knowledge_base_events,
)

router = APIRouter()


def _format_sse(payload: dict) -> str:
    """把事件字典格式化为 SSE 文本帧。

    前端按 event 名分流；data 为 JSON 字符串。
    """
    event_name = payload.get("event") or "message"
    # 去掉 event 字段，其余进 data，避免重复
    data_obj = {key: value for key, value in payload.items() if key != "event"}
    data_text = json.dumps(data_obj, ensure_ascii=False)
    return f"event: {event_name}\ndata: {data_text}\n\n"


@router.post("/ask")
def ask(payload: ChatAskRequest, db: Session = Depends(get_db)):
    """单次知识库问答：检索 + 生成，返回完整答案与引用（非流式兜底）。

    排查：长期无命中时检查文档是否 embedded、Milvus 是否有该 knowledge_base_id 向量。
    """
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
def ask_stream(payload: ChatAskRequest, db: Session = Depends(get_db)):
    """单次知识库流式问答（SSE）。

    事件顺序建议：references → token* → done；失败时 error。
    """

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
