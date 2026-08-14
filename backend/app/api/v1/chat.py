"""智能问答 HTTP 路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatAskRequest, ChatAskRead
from app.schemas.common import error_response, success_response
from app.services.embedding_service import EmbeddingServiceError
from app.services.llm_service import LLMServiceError
from app.services.milvus_service import MilvusServiceError
from app.services.rag_service import RagServiceError, ask_knowledge_base

router = APIRouter()


@router.post("/ask")
def ask(payload: ChatAskRequest, db: Session = Depends(get_db)):
    """单次知识库问答：检索 + 生成，返回完整答案与引用。

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
