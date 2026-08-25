"""RAG 问答编排：检索 → 扩块 → 拼上下文 → LLM 生成（支持非流式 / 流式）。

排查提示：
1. 知识库需有 status=embedded 的文档，否则 Milvus 可能无命中
2. 分数过滤：COSINE 下 score 越大越相似，保留 score >= RAG_SCORE_THRESHOLD
3. 无命中不抛错，返回友好提示文案
4. 流式接口先推 references，再推 token，最后 done
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.schemas.chat import ChatAskRead, ChatReference
from app.services.chunk_service import expand_chunks_for_retrieval
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.milvus_service import MilvusService, get_milvus_service

logger = logging.getLogger(__name__)

# 无检索命中时返回给前端的说明（code 仍为 0）
NO_HIT_ANSWER = "未在该知识库中找到与问题相关的内容，请换个问法或确认文档已完成向量化。"

SYSTEM_PROMPT = (
    "你是企业知识库助手。请仅根据用户提供的【检索上下文】回答问题。"
    "若上下文不足以回答，请明确说明「根据现有资料无法确定」，不要编造。"
    "回答使用简洁中文。"
)


class RagServiceError(RuntimeError):
    """RAG 业务可预期错误（如知识库不存在）。"""

    def __init__(self, message: str, *, http_code: int = 400) -> None:
        super().__init__(message)
        self.http_code = http_code


@dataclass
class SessionStreamGate:
    """会话流式落库闸门：客户端停止/断开后禁止写入 assistant。"""

    allow_persist: bool = True

    def abort(self) -> None:
        """标记客户端已中断，后续不再落 assistant。"""
        self.allow_persist = False


def _allow_persist_assistant(persist_gate: SessionStreamGate | None) -> bool:
    """是否允许写入 assistant（未传 gate 时保持单测/直连调用行为）。"""
    return persist_gate is None or persist_gate.allow_persist


@dataclass
class RetrievalBundle:
    """检索准备结果：供非流式 / 流式共用。"""

    question: str
    knowledge_base_id: int
    # 送入 LLM 的 messages；无命中时为 None
    messages: list[dict] | None
    references: list[ChatReference]
    # 无命中时的友好文案；有命中时为 None
    no_hit_answer: str | None = None
    # 纯检索上下文文本（会话多轮拼 prompt 时用）
    context: str | None = None


def _get_knowledge_base(
    db: Session,
    knowledge_base_id: int,
    *,
    owner_id: int | None = None,
) -> KnowledgeBase | None:
    """按 id 查询知识库；传入 owner_id 时校验归属。"""
    query = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id)
    if owner_id is not None:
        query = query.filter(KnowledgeBase.owner_id == owner_id)
    return query.first()


def _build_context(chunks: list[DocumentChunk], max_chars: int) -> str:
    """将切片拼成送入 LLM 的上下文，超长则截断。"""
    parts: list[str] = []
    used = 0
    for index, chunk in enumerate(chunks, start=1):
        block = (
            f"[引用{index}] document_id={chunk.document_id} chunk_id={chunk.id}\n"
            f"{chunk.content or ''}\n"
        )
        if used + len(block) > max_chars:
            remain = max_chars - used
            if remain <= 0:
                break
            parts.append(block[:remain])
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts).strip()


def _build_references(
    ordered_hits: list[DocumentChunk],
    score_by_id: dict[int, float],
    *,
    preview_limit: int = 300,
) -> list[ChatReference]:
    """把命中切片转成前端引用结构。"""
    references: list[ChatReference] = []
    for hit_chunk in ordered_hits:
        text = hit_chunk.content or ""
        if len(text) > preview_limit:
            text = text[:preview_limit] + "…"
        references.append(
            ChatReference(
                chunk_id=hit_chunk.id,
                document_id=hit_chunk.document_id,
                chunk_index=hit_chunk.chunk_index,
                score=score_by_id.get(hit_chunk.id),
                content=text,
            )
        )
    return references


def prepare_retrieval(
    db: Session,
    *,
    knowledge_base_id: int,
    question: str,
    embedding_service: EmbeddingService | None = None,
    milvus_service: MilvusService | None = None,
    top_k: int | None = None,
    score_threshold: float | None = None,
    max_context_chars: int | None = None,
    owner_id: int | None = None,
) -> RetrievalBundle:
    """完成 Embed + Milvus + 扩块 + 拼 prompt，不调用 LLM。

    流式与非流式共用本函数，避免两套检索逻辑漂移。
    传入 owner_id 时仅允许检索当前用户拥有的知识库。
    """
    question = (question or "").strip()
    if not question:
        raise RagServiceError("问题不能为空", http_code=400)

    kb = _get_knowledge_base(db, knowledge_base_id, owner_id=owner_id)
    if kb is None:
        raise RagServiceError("知识库不存在", http_code=404)

    embedder = embedding_service or get_embedding_service()
    milvus = milvus_service or get_milvus_service()
    k = int(top_k if top_k is not None else settings.rag_top_k)
    threshold = float(
        score_threshold if score_threshold is not None else settings.rag_score_threshold
    )
    max_chars = int(
        max_context_chars if max_context_chars is not None else settings.rag_max_context_chars
    )

    logger.info(
        "RAG 检索: kb_id=%s top_k=%s threshold=%s question_len=%s",
        knowledge_base_id,
        k,
        threshold,
        len(question),
    )

    query_vector = embedder.embed_query(question)
    raw_hits = milvus.search(
        query_vector=query_vector,
        knowledge_base_id=knowledge_base_id,
        top_k=k,
    )

    filtered = [hit for hit in raw_hits if float(hit.get("score") or 0) >= threshold]
    if not filtered:
        logger.info("RAG 无命中: kb_id=%s raw=%s", knowledge_base_id, len(raw_hits))
        return RetrievalBundle(
            question=question,
            knowledge_base_id=knowledge_base_id,
            messages=None,
            references=[],
            no_hit_answer=NO_HIT_ANSWER,
        )

    score_by_id = {int(hit["chunk_id"]): float(hit.get("score") or 0) for hit in filtered}
    chunk_ids = list(score_by_id.keys())
    db_chunks = db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()
    chunk_map = {chunk.id: chunk for chunk in db_chunks}

    ordered_hits: list[DocumentChunk] = []
    for hit in filtered:
        chunk = chunk_map.get(int(hit["chunk_id"]))
        if chunk is not None:
            ordered_hits.append(chunk)

    if not ordered_hits:
        return RetrievalBundle(
            question=question,
            knowledge_base_id=knowledge_base_id,
            messages=None,
            references=[],
            no_hit_answer=NO_HIT_ANSWER,
        )

    expanded = expand_chunks_for_retrieval(db, ordered_hits, max_depth=2)
    context = _build_context(expanded, max_chars)
    if not context:
        return RetrievalBundle(
            question=question,
            knowledge_base_id=knowledge_base_id,
            messages=None,
            references=[],
            no_hit_answer=NO_HIT_ANSWER,
        )

    user_prompt = (
        f"【检索上下文】\n{context}\n\n"
        f"【用户问题】\n{question}\n\n"
        "请依据上下文作答。"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    references = _build_references(ordered_hits, score_by_id)
    logger.info(
        "RAG 检索完成: kb_id=%s hits=%s expanded=%s refs=%s",
        knowledge_base_id,
        len(ordered_hits),
        len(expanded),
        len(references),
    )
    return RetrievalBundle(
        question=question,
        knowledge_base_id=knowledge_base_id,
        messages=messages,
        references=references,
        no_hit_answer=None,
        context=context,
    )


def _build_session_llm_messages(
    *,
    question: str,
    context: str | None,
    history_messages: list,
) -> list[dict]:
    """拼多轮 LLM messages：system + 历史（不含本轮 user）+ 本轮（检索+问题）。

    参数:
        question: 本轮问题。
        context: 检索上下文；无命中时为 None。
        history_messages: ChatMessage 列表（已含本轮 user，正序）。
    """
    # 去掉最后一条（本轮刚写入的 user），避免问题出现两次
    prior = list(history_messages[:-1]) if history_messages else []
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in prior:
        role = (msg.role or "").strip()
        if role not in {"user", "assistant", "system"}:
            continue
        messages.append({"role": role, "content": msg.content or ""})

    if context:
        user_prompt = (
            f"【检索上下文】\n{context}\n\n"
            f"【用户问题】\n{question}\n\n"
            "请依据上下文与对话历史作答。"
        )
    else:
        user_prompt = (
            f"【检索上下文】\n（本轮未检索到相关切片）\n\n"
            f"【用户问题】\n{question}\n\n"
            "若无法依据资料回答，请明确说明。"
        )
    messages.append({"role": "user", "content": user_prompt})
    return messages


def iter_session_ask_events(
    db: Session,
    *,
    session_id: int,
    user_id: int,
    question: str,
    embedding_service: EmbeddingService | None = None,
    milvus_service: MilvusService | None = None,
    llm_service: LLMService | None = None,
    persist_gate: SessionStreamGate | None = None,
) -> Iterator[dict]:
    """会话内流式问答：先落 user → 检索 → SSE → 成功再落 assistant。

    失败或生成器被中断时不落 assistant（由调用方保证不在异常路径写库；
    本函数在完整跑完 token 循环后才写 assistant）。
    """
    from app.services import chat_session_service as session_svc

    question = (question or "").strip()
    if not question:
        raise RagServiceError("问题不能为空", http_code=400)

    session = session_svc.get_session(db, session_id=session_id, user_id=user_id)
    if session is None:
        raise RagServiceError("会话不存在", http_code=404)

    # 1) 先写 user
    session_svc.add_message(db, session_id=session.id, role="user", content=question)
    # 2) 默认标题才自动改
    session_svc.maybe_auto_update_title(db, session, question)

    # 3) 检索（用会话绑定的知识库，并校验归属）
    bundle = prepare_retrieval(
        db,
        knowledge_base_id=session.knowledge_base_id,
        question=question,
        embedding_service=embedding_service,
        milvus_service=milvus_service,
        owner_id=user_id,
    )

    # 4) 历史：最近 N 条 + 字符截断
    recent = session_svc.load_recent_messages(
        db,
        session_id=session.id,
        limit=int(settings.chat_history_max_messages),
    )
    recent = session_svc.truncate_history_by_chars(
        recent,
        int(settings.chat_history_max_chars),
    )

    if bundle.no_hit_answer is not None:
        answer_text = bundle.no_hit_answer
        yield {"event": "references", "references": []}
        yield {"event": "token", "text": answer_text}
        if not _allow_persist_assistant(persist_gate):
            return
        # 无命中也落 assistant（友好提示）；客户端已停止时不落库
        assistant = session_svc.add_message(
            db,
            session_id=session.id,
            role="assistant",
            content=answer_text,
        )
        yield {"event": "done", "ok": True, "assistant_message_id": assistant.id}
        return

    llm_messages = _build_session_llm_messages(
        question=question,
        context=bundle.context,
        history_messages=recent,
    )
    refs_payload = [item.model_dump() for item in bundle.references]
    yield {"event": "references", "references": refs_payload}

    llm = llm_service or get_llm_service()
    parts: list[str] = []
    try:
        for text in llm.chat_stream(llm_messages):
            parts.append(text)
            yield {"event": "token", "text": text}
    except GeneratorExit:
        # 客户端断开 / 停止生成：不落 assistant
        raise
    except Exception as exc:
        # LLM 流式失败：不落 assistant
        logger.exception("会话流式 LLM 失败: session_id=%s", session_id)
        raise RagServiceError(f"LLM 流式失败: {exc}", http_code=502) from exc

    answer_text = "".join(parts).strip()
    if not answer_text:
        raise RagServiceError("LLM 返回空文本", http_code=502)

    if not _allow_persist_assistant(persist_gate):
        return

    assistant = session_svc.add_message(
        db,
        session_id=session.id,
        role="assistant",
        content=answer_text,
    )
    if bundle.references:
        session_svc.add_references_for_message(
            db,
            message_id=assistant.id,
            references=bundle.references,
        )
    yield {"event": "done", "ok": True, "assistant_message_id": assistant.id}


def ask_knowledge_base(
    db: Session,
    *,
    knowledge_base_id: int,
    question: str,
    embedding_service: EmbeddingService | None = None,
    milvus_service: MilvusService | None = None,
    llm_service: LLMService | None = None,
    top_k: int | None = None,
    score_threshold: float | None = None,
    max_context_chars: int | None = None,
    owner_id: int | None = None,
) -> ChatAskRead:
    """对指定知识库执行单次问答（完整 JSON，非流式）。"""
    bundle = prepare_retrieval(
        db,
        knowledge_base_id=knowledge_base_id,
        question=question,
        embedding_service=embedding_service,
        milvus_service=milvus_service,
        top_k=top_k,
        score_threshold=score_threshold,
        max_context_chars=max_context_chars,
        owner_id=owner_id,
    )
    if bundle.no_hit_answer is not None:
        return ChatAskRead(
            answer=bundle.no_hit_answer,
            question=bundle.question,
            knowledge_base_id=bundle.knowledge_base_id,
            references=[],
        )

    llm = llm_service or get_llm_service()
    answer = llm.chat(bundle.messages or [])
    return ChatAskRead(
        answer=answer,
        question=bundle.question,
        knowledge_base_id=bundle.knowledge_base_id,
        references=bundle.references,
    )


def iter_ask_knowledge_base_events(
    db: Session,
    *,
    knowledge_base_id: int,
    question: str,
    embedding_service: EmbeddingService | None = None,
    milvus_service: MilvusService | None = None,
    llm_service: LLMService | None = None,
    top_k: int | None = None,
    score_threshold: float | None = None,
    max_context_chars: int | None = None,
    owner_id: int | None = None,
) -> Iterator[dict]:
    """流式问答：产出前端可消费的事件字典。

    事件类型:
        - references: { "event": "references", "references": [...] }
        - token: { "event": "token", "text": "..." }
        - done: { "event": "done", "ok": true }
        - error: { "event": "error", "message": "..." }（由路由层捕获异常时也可发）
    """
    bundle = prepare_retrieval(
        db,
        knowledge_base_id=knowledge_base_id,
        question=question,
        embedding_service=embedding_service,
        milvus_service=milvus_service,
        top_k=top_k,
        score_threshold=score_threshold,
        max_context_chars=max_context_chars,
        owner_id=owner_id,
    )

    if bundle.no_hit_answer is not None:
        yield {"event": "references", "references": []}
        yield {"event": "token", "text": bundle.no_hit_answer}
        yield {"event": "done", "ok": True}
        return

    yield {
        "event": "references",
        "references": [item.model_dump() for item in bundle.references],
    }

    llm = llm_service or get_llm_service()
    for text in llm.chat_stream(bundle.messages or []):
        yield {"event": "token", "text": text}
    yield {"event": "done", "ok": True}
