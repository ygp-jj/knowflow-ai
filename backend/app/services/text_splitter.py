"""文本切片服务：按固定窗口与 overlap 切分文档页。"""

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120


def split_text(
    pages: list[dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """将解析页列表切成 chunks。

    参数:
        pages: ``[{page_number, content}, ...]``。
        chunk_size: 每个切片最大字符数。
        chunk_overlap: 相邻切片重叠字符数。

    返回:
        ``[{content, page_number, chunk_index}, ...]``，``chunk_index`` 从 0 递增。
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    chunks: list[dict] = []
    chunk_index = 0

    for page in pages:
        content = (page.get("content") or "").strip()
        if not content:
            continue

        page_number = page.get("page_number")
        start = 0
        content_length = len(content)

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
