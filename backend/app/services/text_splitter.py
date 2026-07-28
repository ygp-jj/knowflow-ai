"""文本切片服务：按页做结构化切分（标题/段落优先，滑窗兜底）。

业务约定（见 docs/chunking-service-requirements.md）：
1. 默认 chunk_size=256、chunk_overlap=50，面向内部知识库精准问答。
2. 可通过环境变量 CHUNK_SIZE / CHUNK_OVERLAP（或 Settings）覆盖默认值。
3. 优先按「标题 + 段落」切分；超长段落再按句子/滑窗兜底；空页跳过；
   chunk_index 从 0 全局递增。

对外入口：
- ``split_pages_to_chunks``：正式 API 名（与约束文档一致）
- ``split_text``：兼容别名，行为与正式入口相同
"""

from __future__ import annotations
import re

_BOUNDARY_CHARS = set("。！？；：\n\r")
_SENTENCE_SEP_PATTERN = re.compile(r"([。！？；])")
_MARKDOWN_TITLE_PATTERN = re.compile(r"^(#{1,6})\s*(.+?)\s*$")
_CN_CHAPTER_PATTERN = re.compile(r"^(第[一二三四五六七八九十百千万零0-9]+[章节篇])\s*(.*)$")
_CN_ITEM_PATTERN = re.compile(r"^([一二三四五六七八九十]+[、.．])\s*(.+)$")
_CN_SUB_ITEM_PATTERN = re.compile(r"^(（[一二三四五六七八九十0-9]+）)\s*(.+)$")
_DIGIT_ITEM_PATTERN = re.compile(r"^(\d+(?:\.\d+){0,3})[、.．\s]+(.+)$")
_INLINE_TITLE_BREAK_PATTERN = re.compile(
    r"([。！？；：:\n\r])\s*"
    r"(第[一二三四五六七八九十百千万零0-9]+[章节篇]"
    r"|[一二三四五六七八九十]+[、.．]"
    r"|（[一二三四五六七八九十0-9]+）)"
)


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


def _detect_title(line: str) -> tuple[int, str] | None:
    """识别标题行，返回 (层级, 标题文本)。"""

    text = line.strip()
    if not text:
        return None

    markdown_match = _MARKDOWN_TITLE_PATTERN.match(text)
    if markdown_match:
        level = len(markdown_match.group(1))
        title = markdown_match.group(2).strip()
        return (level, title) if title else None

    chapter_match = _CN_CHAPTER_PATTERN.match(text)
    if chapter_match:
        title = f"{chapter_match.group(1)} {chapter_match.group(2)}".strip()
        return 1, title

    cn_item_match = _CN_ITEM_PATTERN.match(text)
    if cn_item_match:
        return 2, text

    cn_sub_item_match = _CN_SUB_ITEM_PATTERN.match(text)
    if cn_sub_item_match:
        return 3, text

    digit_item_match = _DIGIT_ITEM_PATTERN.match(text)
    if digit_item_match and len(digit_item_match.group(1)) <= 12:
        level = digit_item_match.group(1).count(".") + 2
        return level, text

    return None


def _extract_structured_blocks(content: str) -> list[dict]:
    """从原始文本中提取结构化块（标题块/段落块）。"""

    # 处理“标题与上一句粘连在同一行”的情况，强制在标题前断行。
    normalized_content = _INLINE_TITLE_BREAK_PATTERN.sub(r"\1\n\2", content)

    blocks: list[dict] = []
    paragraph_lines: list[str] = []
    section_title: str | None = None
    section_level: int | None = None
    paragraph_index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_index
        if not paragraph_lines:
            return
        paragraph_text = "\n".join(line.strip() for line in paragraph_lines if line.strip()).strip()
        paragraph_lines.clear()
        if not paragraph_text:
            return
        blocks.append({
            "text": paragraph_text,
            "boundary_type": "paragraph",
            "section_title": section_title,
            "section_level": section_level,
            "paragraph_index": paragraph_index,
        })
        paragraph_index += 1

    for raw_line in normalized_content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue

        title = _detect_title(stripped)
        if title:
            flush_paragraph()
            section_level, section_title = title
            blocks.append({
                "text": stripped,
                "boundary_type": "title",
                "section_title": section_title,
                "section_level": section_level,
                "paragraph_index": None,
            })
            continue

        paragraph_lines.append(stripped)

    flush_paragraph()
    if blocks:
        return blocks

    # 没有换行结构时退化为一个段落块。
    merged = content.strip()
    return [{
        "text": merged,
        "boundary_type": "paragraph",
        "section_title": None,
        "section_level": None,
        "paragraph_index": 0,
    }] if merged else []


def _split_by_sentences(text: str) -> list[str]:
    """按中文句末标点切句，保留分隔符。"""

    if not text:
        return []

    parts = _SENTENCE_SEP_PATTERN.split(text.replace("\r", "\n"))
    sentences: list[str] = []
    for idx in range(0, len(parts), 2):
        body = parts[idx].strip()
        sep = parts[idx + 1] if idx + 1 < len(parts) else ""
        sentence = f"{body}{sep}".strip()
        if sentence:
            sentences.append(sentence)
    return sentences if sentences else [text.strip()]


def _split_long_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    base_metadata: dict,
) -> list[dict]:
    """超长文本切分：句子优先，单句过长时滑窗兜底。"""

    pieces: list[dict] = []
    sentence_chunks: list[str] = []
    current = ""

    for sentence in _split_by_sentences(text):
        if len(sentence) <= chunk_size:
            candidate = sentence if not current else f"{current}\n{sentence}"
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    sentence_chunks.append(current)
                current = sentence
            continue

        if current:
            sentence_chunks.append(current)
            current = ""

        start = 0
        sentence_len = len(sentence)
        while start < sentence_len:
            hard_end = min(start + chunk_size, sentence_len)
            end = _align_chunk_end(sentence, start, hard_end)
            chunk_text = sentence[start:end].strip()
            if chunk_text:
                piece_meta = dict(base_metadata)
                piece_meta["boundary_type"] = "sliding"
                pieces.append({"content": chunk_text, "metadata": piece_meta})
            if end >= sentence_len:
                break
            next_start = max(start + 1, end - chunk_overlap)
            start = _align_next_start(sentence, next_start, end)

    if current:
        sentence_chunks.append(current)

    for chunk_text in sentence_chunks:
        piece_meta = dict(base_metadata)
        piece_meta["boundary_type"] = "sentence"
        pieces.append({"content": chunk_text, "metadata": piece_meta})

    return pieces


def _align_chunk_end(content: str, start: int, end: int) -> int:
    """尽量把切片结尾对齐到句子/行边界，减少断句。"""

    if end >= len(content):
        return end

    # 只在窗口后 40% 区间回溯，避免切片过短。
    min_end = start + max(1, int((end - start) * 0.6))
    for idx in range(end - 1, min_end - 1, -1):
        if content[idx] in _BOUNDARY_CHARS:
            return idx + 1
    return end


def _align_next_start(content: str, start: int, end: int) -> int:
    """把下一片起点前移到最近边界后，避免从词中间开头。"""

    if start <= 0:
        return 0

    search_end = min(len(content), max(start + 1, start + 30, end))
    for idx in range(start, search_end):
        if content[idx] in _BOUNDARY_CHARS:
            return idx + 1
    return start


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
        structured_blocks = _extract_structured_blocks(content)
        current_chunk = ""
        current_meta: dict | None = None

        def flush_current_chunk() -> None:
            nonlocal current_chunk, current_meta, chunk_index
            chunk_text = current_chunk.strip()
            if not chunk_text:
                current_chunk = ""
                current_meta = None
                return

            last_content = chunks[-1]["content"] if chunks else None
            if chunk_text == last_content:
                current_chunk = ""
                current_meta = None
                return

            chunk_item = {
                "content": chunk_text,
                "page_number": page_number,
                "chunk_index": chunk_index,
            }
            if current_meta:
                chunk_item["metadata"] = current_meta
            chunks.append(chunk_item)
            chunk_index += 1
            current_chunk = ""
            current_meta = None

        for block in structured_blocks:
            block_text = block["text"]
            block_meta = {
                "boundary_type": block["boundary_type"],
                "section_title": block.get("section_title"),
                "section_level": block.get("section_level"),
                "paragraph_index": block.get("paragraph_index"),
            }

            # 遇到新标题时先落盘当前 chunk，避免跨标题拼接在同一块中。
            if block["boundary_type"] == "title" and current_chunk:
                flush_current_chunk()

            if len(block_text) > chunk_size:
                flush_current_chunk()
                for piece in _split_long_text(block_text, chunk_size, chunk_overlap, block_meta):
                    chunk_text = piece["content"]
                    last_content = chunks[-1]["content"] if chunks else None
                    if chunk_text == last_content:
                        continue
                    chunks.append({
                        "content": chunk_text,
                        "page_number": page_number,
                        "chunk_index": chunk_index,
                        "metadata": piece["metadata"],
                    })
                    chunk_index += 1
                continue

            candidate = block_text if not current_chunk else f"{current_chunk}\n{block_text}"
            if len(candidate) <= chunk_size:
                current_chunk = candidate
                if current_meta is None:
                    current_meta = dict(block_meta)
                else:
                    current_meta["boundary_type"] = "paragraph_pack"
                continue

            flush_current_chunk()
            current_chunk = block_text
            current_meta = dict(block_meta)

        flush_current_chunk()

    return chunks


# 兼容旧调用名；新代码请优先使用 split_pages_to_chunks。
split_text = split_pages_to_chunks
