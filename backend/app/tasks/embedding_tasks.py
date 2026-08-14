"""文档向量化 Celery 任务（第 4 阶段）。

状态流转：
    chunked → embedding → embedded
                   ↘ failed

排查提示：
1. Worker 需加载本模块：celery include 含 app.tasks.embedding_tasks
2. 失败时看 documents.error_message，以及 Worker 日志中的 Embedding/Milvus 异常
3. 重新向量化会先删该文档旧向量，再写入新向量并回填 vector_id
"""

from __future__ import annotations

import logging

from app.core.database import SessionLocal
from app.models.chunk import DocumentChunk
from app.services.document_service import get_document
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError, get_embedding_service
from app.services.milvus_service import MilvusService, MilvusServiceError, get_milvus_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

STATUS_EMBEDDING = "embedding"
STATUS_EMBEDDED = "embedded"
STATUS_FAILED = "failed"


def _update_document_status(db, document, status: str, error_message: str | None = None) -> None:
    """更新文档状态并提交；前端刷新列表时可看到 status / error_message。"""
    document.status = status
    document.error_message = error_message
    db.commit()
    db.refresh(document)


def run_embed_document(
    document_id: int,
    *,
    embedding_service: EmbeddingService | None = None,
    milvus_service: MilvusService | None = None,
) -> dict:
    """同步执行文档向量化主流程（可供 Celery 或单测调用）。

    步骤：
        1. 校验文档存在且已有切片
        2. 状态改为 embedding
        3. 读取全部 document_chunks（含父块/子块，均需向量化）
        4. 批量 Embedding
        5. 清理该文档旧 Milvus 向量后写入新向量
        6. 回填 chunks.vector_id
        7. 状态改为 embedded

    返回:
        {document_id, status, embedded_count?} 或失败时的 error 字段。
    """
    db = SessionLocal()
    embedder = embedding_service or get_embedding_service()
    milvus = milvus_service or get_milvus_service()

    try:
        document = get_document(db, document_id)
        if document is None:
            return {"document_id": document_id, "status": STATUS_FAILED, "error": "文档不存在"}

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        if not chunks:
            raise ValueError("文档没有切片，无法向量化；请先完成切片（status=chunked）")

        _update_document_status(db, document, STATUS_EMBEDDING, error_message=None)
        logger.info(
            "开始向量化: document_id=%s chunk_count=%s kb_id=%s",
            document_id,
            len(chunks),
            document.knowledge_base_id,
        )

        texts = [chunk.content or "" for chunk in chunks]
        vectors = embedder.embed_texts(texts)
        if len(vectors) != len(chunks):
            raise EmbeddingServiceError(
                f"向量条数与切片数不一致: chunks={len(chunks)} vectors={len(vectors)}"
            )

        # 先清旧向量，避免重复主键 / 脏数据
        milvus.delete_by_document_id(document_id)

        rows = []
        for chunk, vector in zip(chunks, vectors):
            rows.append({
                "chunk_id": chunk.id,
                "document_id": document.id,
                "knowledge_base_id": document.knowledge_base_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content or "",
                "embedding": vector,
            })
        vector_ids = milvus.upsert_chunk_embeddings(rows)

        for chunk, vector_id in zip(chunks, vector_ids):
            chunk.vector_id = vector_id
        db.commit()

        _update_document_status(db, document, STATUS_EMBEDDED, error_message=None)
        logger.info(
            "向量化完成: document_id=%s embedded_count=%s",
            document_id,
            len(chunks),
        )
        return {
            "document_id": document_id,
            "status": STATUS_EMBEDDED,
            "embedded_count": len(chunks),
        }

    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        if isinstance(exc, (EmbeddingServiceError, MilvusServiceError, ValueError)):
            message = str(exc)
        logger.exception("向量化失败: document_id=%s error=%s", document_id, message)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            logger.exception("向量化失败后 rollback 异常: document_id=%s", document_id)
        if "document" in locals() and document is not None:
            try:
                # 重新绑定到当前 session，避免先前 flush 失败后对象脏状态
                document = get_document(db, document_id)
                if document is not None:
                    _update_document_status(db, document, STATUS_FAILED, error_message=message[:2000])
            except Exception:  # noqa: BLE001
                logger.exception("写入 failed 状态失败: document_id=%s", document_id)
        return {
            "document_id": document_id,
            "status": STATUS_FAILED,
            "error": message,
        }
    finally:
        db.close()


@celery_app.task(name="app.tasks.embedding_tasks.embed_document")
def embed_document(document_id: int) -> dict:
    """【异步入口】前端触发向量化后投递到此任务。

    前端观察 documents.status：
      - embedding → 处理中
      - embedded → 成功，可进入检索问答
      - failed → 查看 error_message
    """
    return run_embed_document(document_id)
