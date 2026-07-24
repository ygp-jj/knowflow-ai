"""文本切片服务：按页做固定窗口滑动切分。

业务约定（见 docs/chunking-service-requirements.md）：
1. 默认 chunk_size=256、chunk_overlap=50，面向内部知识库精准问答。
2. 可通过环境变量 CHUNK_SIZE / CHUNK_OVERLAP（或 Settings）覆盖默认值。
3. 按「页内滑动窗口」切分，不是一页一块；空页跳过；chunk_index 从 0 全局递增。

对外入口：
- ``split_pages_to_chunks``：正式 API 名（与约束文档一致）
- ``split_text``：兼容别名，行为与正式入口相同
"""

from __future__ import annotations


def _resolve_chunk_defaults() -> tuple[int, int]:
    """读取配置中心的默认切分参数。

    返回:
        (chunk_size, chunk_overlap)；读取失败时回退为 (256, 50)。
    """

    try:
        from app.core.config import settings

        return settings.chunk_size, settings.chunk_overlap
    except Exception:
        return 256, 50


# 模块级默认值（与 Settings 一致，便于单测直接断言，无需加载完整配置）。
DEFAULT_CHUNK_SIZE = 256
DEFAULT_CHUNK_OVERLAP = 50


def split_pages_to_chunks(
    pages: list[dict],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """将解析后的页列表按页内滑动窗口切成文本块。

    参数:
        pages: 页列表，每项形如 ``{"page_number": int|None, "content": str}``。
        chunk_size: 单块最大字符数；传 None 时取配置或模块默认 256。
        chunk_overlap: 相邻块重叠字符数；传 None 时取配置或模块默认 50。

    返回:
        切片列表，每项形如 ``{"content", "page_number", "chunk_index"}``；
        ``chunk_index`` 从 0 起按产出顺序全局递增（跨页连续）。

    异常:
        ValueError: 参数非法（大小 <= 0、overlap 为负、或 overlap >= chunk_size）。
    """

    # 未显式传入时，回落到配置 / 模块默认值。
    if chunk_size is None or chunk_overlap is None:
        default_size, default_overlap = _resolve_chunk_defaults()
        if chunk_size is None:
            chunk_size = default_size
        if chunk_overlap is None:
            chunk_overlap = default_overlap

    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    # 累计产出的切片；chunk_index 跨页连续编号。
    chunks: list[dict] = []
    chunk_index = 0

    for page in pages:
        # 空页（含仅空白）不产出切片。
        content = (page.get("content") or "").strip()
        if not content:
            continue

        page_number = page.get("page_number")
        start = 0
        content_length = len(content)

        # 页内滑动窗口：每次前进 (chunk_size - chunk_overlap)。
        while start < content_length:
            end = min(start + chunk_size, content_length)
            chunk_text = content[start:end].strip()

            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

            if end >= content_length:
                break

            start = end - chunk_overlap

    return chunks


# 兼容旧调用名；新代码请优先使用 split_pages_to_chunks。
split_text = split_pages_to_chunks
