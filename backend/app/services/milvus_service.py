"""Milvus 向量库服务：负责 collection 初始化、写入与按文档清理。

排查提示：
1. 确认 docker compose 中 milvus/etcd/minio 已启动，端口 19530 可连通
2. EMBEDDING_DIMENSION 变更后需重建 collection（旧库维度不兼容）
3. 写入失败时看日志中的 collection / dim / 行数
4. 删除文档时会 best-effort 清理向量；Milvus 宕机不应阻塞 PG 删除（由上层决定）
"""

from __future__ import annotations

import logging
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# 连接别名：同一进程内复用，避免重复 connect
_MILVUS_ALIAS = "knowflow_default"


class MilvusServiceError(RuntimeError):
    """Milvus 操作失败。"""


class MilvusService:
    """文档切片向量的 Milvus 读写封装。"""

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        collection_name: str | None = None,
        dimension: int | None = None,
    ) -> None:
        """初始化 Milvus 配置（真正建连在 ensure_collection / 写读时触发）。

        参数:
            host/port: Milvus 地址；默认取 settings。
            collection_name: collection 名；默认 document_chunks。
            dimension: 向量维度；必须与 Embedding 输出一致。
        """
        self.host = host or settings.milvus_host
        self.port = int(port if port is not None else settings.milvus_port)
        self.collection_name = collection_name or settings.milvus_collection
        self.dimension = int(dimension if dimension is not None else settings.embedding_dimension)

    def _connect(self) -> None:
        """建立或复用 Milvus 连接。"""
        try:
            if connections.has_connection(_MILVUS_ALIAS):
                return
            connections.connect(
                alias=_MILVUS_ALIAS,
                host=self.host,
                port=str(self.port),
            )
            logger.info("Milvus 已连接: %s:%s alias=%s", self.host, self.port, _MILVUS_ALIAS)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Milvus 连接失败: %s:%s", self.host, self.port)
            raise MilvusServiceError(f"Milvus 连接失败: {exc}") from exc

    def ensure_collection(self) -> Collection:
        """确保 collection 存在并已 load；不存在则按当前维度创建。

        Schema:
            - chunk_id (PK, INT64): 与 PostgreSQL document_chunks.id 对齐，便于排查
            - document_id / knowledge_base_id / chunk_index
            - content: 冗余正文，检索阶段可先看命中文本
            - embedding: FLOAT_VECTOR
        """
        self._connect()
        try:
            if utility.has_collection(self.collection_name, using=_MILVUS_ALIAS):
                collection = Collection(self.collection_name, using=_MILVUS_ALIAS)
                collection.load()
                return collection

            fields = [
                FieldSchema(name="chunk_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
                FieldSchema(name="document_id", dtype=DataType.INT64),
                FieldSchema(name="knowledge_base_id", dtype=DataType.INT64),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            ]
            schema = CollectionSchema(
                fields=fields,
                description="KnowFlow document chunk embeddings",
            )
            collection = Collection(
                name=self.collection_name,
                schema=schema,
                using=_MILVUS_ALIAS,
            )
            # IVF_FLAT 适合中小规模知识库；nlist 可后续按数据量调优
            collection.create_index(
                field_name="embedding",
                index_params={
                    "index_type": "IVF_FLAT",
                    "metric_type": "COSINE",
                    "params": {"nlist": 1024},
                },
            )
            collection.load()
            logger.info(
                "Milvus collection 已创建: name=%s dim=%s",
                self.collection_name,
                self.dimension,
            )
            return collection
        except Exception as exc:  # noqa: BLE001
            logger.exception("Milvus ensure_collection 失败: %s", self.collection_name)
            raise MilvusServiceError(f"Milvus collection 初始化失败: {exc}") from exc

    def delete_by_document_id(self, document_id: int) -> None:
        """删除某文档在 Milvus 中的全部向量（重新向量化前调用）。"""
        collection = self.ensure_collection()
        expr = f"document_id == {int(document_id)}"
        try:
            collection.delete(expr)
            logger.info("已清理文档向量: document_id=%s expr=%s", document_id, expr)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Milvus 按文档删除失败: document_id=%s", document_id)
            raise MilvusServiceError(f"Milvus 删除文档向量失败: {exc}") from exc

    def upsert_chunk_embeddings(self, rows: list[dict[str, Any]]) -> list[str]:
        """写入（覆盖）切片向量。

        参数 rows 每项需包含:
            chunk_id, document_id, knowledge_base_id, chunk_index, content, embedding

        返回:
            与输入对应的 vector_id 列表（当前实现为 str(chunk_id)，便于 PG 回填与排查）。
        """
        if not rows:
            return []

        collection = self.ensure_collection()

        # 先删同 chunk_id，模拟 upsert，避免主键冲突
        chunk_ids = [int(row["chunk_id"]) for row in rows]
        id_list = ", ".join(str(item) for item in chunk_ids)
        try:
            collection.delete(f"chunk_id in [{id_list}]")
        except Exception:  # noqa: BLE001
            # 首次写入或表达式空集时 delete 可能报错，记录后继续 insert
            logger.warning("Milvus 预删除 chunk 时出现异常（可忽略若集合为空）: ids=%s", chunk_ids[:5])

        # VARCHAR 有上限，超长正文截断，完整正文仍在 PostgreSQL
        max_content_len = 60000
        entities = [
            [int(row["chunk_id"]) for row in rows],
            [int(row["document_id"]) for row in rows],
            [int(row["knowledge_base_id"]) for row in rows],
            [int(row["chunk_index"]) for row in rows],
            [(row.get("content") or "")[:max_content_len] for row in rows],
            [list(row["embedding"]) for row in rows],
        ]
        try:
            collection.insert(entities)
            collection.flush()
            logger.info(
                "Milvus 写入完成: collection=%s rows=%s document_id=%s",
                self.collection_name,
                len(rows),
                rows[0].get("document_id"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Milvus insert 失败: rows=%s", len(rows))
            raise MilvusServiceError(f"Milvus 写入向量失败: {exc}") from exc

        return [str(chunk_id) for chunk_id in chunk_ids]

    def search(
        self,
        *,
        query_vector: list[float],
        knowledge_base_id: int,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """按知识库过滤做向量检索（供后续问答阶段使用）。

        返回字段: chunk_id / document_id / chunk_index / content / score
        """
        collection = self.ensure_collection()
        try:
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"nprobe": 16}},
                limit=top_k,
                expr=f"knowledge_base_id == {int(knowledge_base_id)}",
                output_fields=["chunk_id", "document_id", "chunk_index", "content"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Milvus search 失败: knowledge_base_id=%s top_k=%s",
                knowledge_base_id,
                top_k,
            )
            raise MilvusServiceError(f"Milvus 检索失败: {exc}") from exc

        hits: list[dict[str, Any]] = []
        if not results:
            return hits
        for hit in results[0]:
            entity = hit.entity
            hits.append({
                "chunk_id": int(entity.get("chunk_id")),
                "document_id": int(entity.get("document_id")),
                "chunk_index": int(entity.get("chunk_index")),
                "content": entity.get("content") or "",
                "score": float(hit.distance),
            })
        return hits


def get_milvus_service() -> MilvusService:
    """获取默认 MilvusService 实例。"""
    return MilvusService()
