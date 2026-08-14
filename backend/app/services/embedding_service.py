"""Embedding 服务：调用 OpenAI 兼容接口生成文本向量。

排查提示：
1. 检查 .env 中 EMBEDDING_BASE_URL / EMBEDDING_API_KEY / EMBEDDING_MODEL / EMBEDDING_DIMENSION
2. 维度必须与 Milvus collection 一致，否则写入会失败
3. 批量过大时上游可能超时，可调小 EMBEDDING_BATCH_SIZE
"""

from __future__ import annotations

import logging

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    """Embedding 调用失败（鉴权、网络、模型或返回格式异常）。"""


class EmbeddingService:
    """OpenAI 兼容 Embedding 客户端。"""

    def __init__(
        self,
        *,
        client: OpenAI | None = None,
        model: str | None = None,
        dimension: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        """初始化 Embedding 客户端。

        参数:
            client: 可注入的 OpenAI 客户端（单测用）；默认按配置新建。
            model: 模型名；默认取 settings.embedding_model。
            dimension: 期望向量维度；用于结果校验。
            batch_size: 单次请求最多条数；默认 16。
        """
        self.client = client or OpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
        )
        self.model = model or settings.embedding_model
        self.dimension = dimension if dimension is not None else settings.embedding_dimension
        self.batch_size = batch_size if batch_size is not None else int(
            getattr(settings, "embedding_batch_size", 16) or 16
        )
        if self.batch_size <= 0:
            raise ValueError("embedding_batch_size 必须大于 0")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转为向量列表（保持输入顺序）。

        参数:
            texts: 待向量化文本；空串会被替换为空格，避免部分上游拒绝空 input。

        返回:
            与 texts 等长的向量列表。

        异常:
            EmbeddingServiceError: 上游失败或维度不匹配。
        """
        if not texts:
            return []

        # 规范化空文本，避免部分兼容接口因空字符串直接 400
        normalized = [text if text and text.strip() else " " for text in texts]
        vectors: list[list[float]] = []

        for start in range(0, len(normalized), self.batch_size):
            batch = normalized[start:start + self.batch_size]
            batch_index = start // self.batch_size
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Embedding 请求失败: model=%s batch=%s size=%s",
                    self.model,
                    batch_index,
                    len(batch),
                )
                raise EmbeddingServiceError(
                    f"Embedding 请求失败（batch={batch_index}）: {exc}"
                ) from exc

            data = list(getattr(response, "data", []) or [])
            # 部分实现不保证按 index 排序，这里显式排序后再取 embedding
            data.sort(key=lambda item: getattr(item, "index", 0))
            if len(data) != len(batch):
                raise EmbeddingServiceError(
                    f"Embedding 返回条数不匹配: 期望 {len(batch)}，实际 {len(data)}"
                )

            for item in data:
                vector = list(getattr(item, "embedding", []) or [])
                if self.dimension and len(vector) != self.dimension:
                    raise EmbeddingServiceError(
                        f"Embedding 维度不匹配: 期望 {self.dimension}，实际 {len(vector)}；"
                        "请检查 EMBEDDING_MODEL 与 EMBEDDING_DIMENSION"
                    )
                vectors.append(vector)

        return vectors

    def embed_query(self, query: str) -> list[float]:
        """对单条查询文本生成向量（检索阶段复用）。"""
        return self.embed_texts([query])[0]


def get_embedding_service() -> EmbeddingService:
    """获取默认 EmbeddingService 实例。"""
    return EmbeddingService()
