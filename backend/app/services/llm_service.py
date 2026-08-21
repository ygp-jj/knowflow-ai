"""LLM 对话服务：调用 OpenAI 兼容 Chat Completions（DeepSeek 等）。

排查提示：
1. 检查 .env 中 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
2. 本机需能访问 LLM 地址（DeepSeek 一般可达）
3. 超时或 401 时看 Worker/API 日志中的完整异常
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMServiceError(RuntimeError):
    """LLM 调用失败。"""


class LLMService:
    """OpenAI 兼容聊天客户端。"""

    def __init__(
        self,
        *,
        client: OpenAI | None = None,
        model: str | None = None,
    ) -> None:
        """初始化 LLM 客户端。

        参数:
            client: 可注入客户端（单测用）。
            model: 模型名；默认 settings.llm_model。
        """
        self.client = client or OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.model = model or settings.llm_model

    def chat(self, messages: list[dict[str, Any]], *, temperature: float = 0.2) -> str:
        """发送多轮 messages，返回助手文本。

        参数:
            messages: OpenAI 风格 [{role, content}, ...]
            temperature: 采样温度；问答场景默认偏低以减少胡编。
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM 请求失败: model=%s", self.model)
            raise LLMServiceError(f"LLM 请求失败: {exc}") from exc

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise LLMServiceError("LLM 返回为空（无 choices）")
        message = choices[0].message
        content = (getattr(message, "content", None) or "").strip()
        if not content:
            raise LLMServiceError("LLM 返回空文本")
        return content

    def chat_stream(self, messages: list[dict[str, Any]], *, temperature: float = 0.2):
        """流式生成助手文本，逐段 yield 增量字符串。

        参数:
            messages: OpenAI 风格消息列表。
            temperature: 采样温度。

        产出:
            非空增量文本片段（可能是单字或短词，取决于上游）。
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM 流式请求失败: model=%s", self.model)
            raise LLMServiceError(f"LLM 流式请求失败: {exc}") from exc

        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            text = getattr(delta, "content", None) if delta is not None else None
            if text:
                yield text


def get_llm_service() -> LLMService:
    """获取默认 LLMService 实例。"""
    return LLMService()
