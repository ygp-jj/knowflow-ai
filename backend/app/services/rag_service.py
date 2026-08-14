"""RAG 问答编排：检索 → 扩块 → 拼上下文 → LLM 生成。

排查提示：
1. 知识库需有 status=embedded 的文档，否则 Milvus 可能无命中
2. 分数过滤：COSINE 下 score 越大越相似，保留 score >= RAG_SCORE_THRESHOLD
3. 无命中不抛错，返回友好提示文案
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.schemas.chat import ChatAskRead, ChatReference
from app.services.chunk_service import expand_chunks_for_retrieval
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError, get_embedding_service
from app.services.llm_service import LLMService, LLMServiceError, get_llm_service
from app.services.milvus_service import MilvusService, MilvusServiceError, get_milvus_service

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
class _ScoredChunk:
    """带检索分数的切片，便于拼引用。"""

    chunk: DocumentChunk
    score: float | None


def _get_knowledge_base(db: Session, knowledge_base_id: int) -> KnowledgeBase | None:
    """按 id 查询知识库（问答第一版不校验 owner）。"""
    return db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()


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
) -> ChatAskRead:
    """对指定知识库执行单次问答。

    异常:
        RagServiceError: 知识库不存在等业务错误。
        EmbeddingServiceError / MilvusServiceError / LLMServiceError: 下游失败。
    """
    question = (question or "").strip()
    if not question:
        raise RagServiceError("问题不能为空", http_code=400)

    kb = _get_knowledge_base(db, knowledge_base_id)
    if kb is None:
        raise RagServiceError("知识库不存在", http_code=404)

    embedder = embedding_service or get_embedding_service()
    milvus = milvus_service or get_milvus_service()
    llm = llm_service or get_llm_service()
    k = int(top_k if top_k is not None else settings.rag_top_k)
    threshold = float(
        score_threshold if score_threshold is not None else settings.rag_score_threshold
    )
    max_chars = int(
        max_context_chars if max_context_chars is not None else settings.rag_max_context_chars
    )

    logger.info(
        "RAG 开始: kb_id=%s top_k=%s threshold=%s question_len=%s",
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

    # COSINE：score 越大越相似，保留 >= threshold
    filtered = [hit for hit in raw_hits if float(hit.get("score") or 0) >= threshold]
    if not filtered:
        logger.info("RAG 无命中: kb_id=%s raw=%s", knowledge_base_id, len(raw_hits))
        return ChatAskRead(
            answer=NO_HIT_ANSWER,
            question=question,
            knowledge_base_id=knowledge_base_id,
            references=[],
        )

    score_by_id = {int(hit["chunk_id"]): float(hit.get("score") or 0) for hit in filtered}
    chunk_ids = list(score_by_id.keys())
    db_chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )
    chunk_map = {chunk.id: chunk for chunk in db_chunks}

    # 保持 Milvus 命中顺序
    ordered_hits: list[DocumentChunk] = []
    for hit in filtered:
        chunk = chunk_map.get(int(hit["chunk_id"]))
        if chunk is not None:
            ordered_hits.append(chunk)

    if not ordered_hits:
        return ChatAskRead(
            answer=NO_HIT_ANSWER,
            question=question,
            knowledge_base_id=knowledge_base_id,
            references=[],
        )

    expanded = expand_chunks_for_retrieval(db, ordered_hits, max_depth=2)
    context = _build_context(expanded, max_chars)
    if not context:
        return ChatAskRead(
            answer=NO_HIT_ANSWER,
            question=question,
            knowledge_base_id=knowledge_base_id,
            references=[],
        )

    user_prompt = (
        f"【检索上下文】\n{context}\n\n"
        f"【用户问题】\n{question}\n\n"
        "请依据上下文作答。"
    )
    answer = llm.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    # 引用展示：优先展示原始命中块（带 score），内容可截断
    preview_limit = 300
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

    logger.info(
        "RAG 完成: kb_id=%s hits=%s expanded=%s refs=%s",
        knowledge_base_id,
        len(ordered_hits),
        len(expanded),
        len(references),
    )
    return ChatAskRead(
        answer=answer,
        question=question,
        knowledge_base_id=knowledge_base_id,
        references=references,
    )
