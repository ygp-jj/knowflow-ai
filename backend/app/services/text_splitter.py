"""文本切片服务：按页做结构化切分（标题层级优先，滑窗兜底）。

业务约定（见 docs/chunking-service-requirements.md）：
1. 默认 chunk_size=256、chunk_overlap=50，面向内部知识库精准问答。
2. 可通过环境变量 CHUNK_SIZE / CHUNK_OVERLAP（或 Settings）覆盖默认值。
3. 标题按层级切分；支持 chunk_profile=auto/policy/diary：
   - policy：章/节/篇 > 条 > 一、 > 1. > 1.1
   - diary：日期 > 今日反思/金句；正文按段落落块（超长段再滑窗）
   大标题独立成块；子块通过 parent_chunk_index 挂父块；
   空页跳过；chunk_index 从 0 全局递增。

对外入口：
- ``split_pages_to_chunks``：正式 API 名（与约束文档一致）
- ``split_text``：兼容别名，行为与正式入口相同
"""

from __future__ import annotations
import re

_BOUNDARY_CHARS = set("。！？；：\n\r")
_SENTENCE_SEP_PATTERN = re.compile(r"([。！？；])")
_MARKDOWN_TITLE_PATTERN = re.compile(r"^(#{1,6})\s*(.+?)\s*$")
# 层级约定：章/节/篇=1，条=2，一、/二、=3，1.=4，1.1=5，（一）=5
# 注意：1. 必须比 一、 更深，否则父栈会把「三、」弹掉，子块丢失 parent
MAJOR_TITLE_MAX_LEVEL = 2
_CN_CHAPTER_PATTERN = re.compile(r"^(第[一二三四五六七八九十百千万零0-9]+[章节篇])\s*(.*)$")
_CN_ARTICLE_PATTERN = re.compile(r"^(第[一二三四五六七八九十百千万零0-9]+条)\s*(.*)$")
_CN_ITEM_PATTERN = re.compile(r"^([一二三四五六七八九十]+[、.．])\s*(.+)$")
_CN_SUB_ITEM_PATTERN = re.compile(r"^(（[一二三四五六七八九十0-9]+）)\s*(.+)$")
_DIGIT_ITEM_PATTERN = re.compile(r"^(\d+(?:\.\d+){0,3})[、.．\s]+(.+)$")
# 「一、放假时间 2026年…」→ 标题名与后接正文拆开
_CN_ITEM_TITLE_BODY_PATTERN = re.compile(
    r"^([一二三四五六七八九十]+[、.．])\s*"
    r"([^\s\d。；;]{1,20}?)"
    r"(?:\s+|(?=\d)|(?=[。；;])|$)"
    r"(.*)$"
)
_INLINE_TITLE_BREAK_PATTERN = re.compile(
    r"([。！？；：:\n\r])\s*"
    r"(第[一二三四五六七八九十百千万零0-9]+[章节篇条]"
    r"|[一二三四五六七八九十]+[、.．]"
    r"|（[一二三四五六七八九十0-9]+）)"
)
# 即使缺少句读，也在「一、/二、/第X条」前强制断行（避免并进前言段）
_FORCE_BREAK_BEFORE_SECTION_PATTERN = re.compile(
    r"(?<=.)(?<![一二三四五六七八九十百千])"
    r"(?=(?:[一二三四五六七八九十]+[、.．]|第[一二三四五六七八九十百千万零0-9]+[章节篇条]))"
)
# 日记：日期标题（整行基本是日期，兼容「| 周五」「（周五）」「 周五」）
_DIARY_DATE_PATTERN = re.compile(
    r"^(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)"
    r"(?:"
    r"\s*[|｜]\s*周[一二三四五六日天]"
    r"|\s*[（(]\s*周[一二三四五六日天]\s*[）)]"
    r"|\s+周[一二三四五六日天]"
    r")?"
    r"\s*$"
)
# 正文中的日期片段（用于弱信号，不要求独占一行）
_DIARY_DATE_LOOSE_PATTERN = re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日")
# 日记：固定小节标签
_DIARY_SECTION_LABELS = ("今日反思", "今日金句", "今日总结", "今日收获", "今日待办")
_DIARY_SECTION_LABEL_PATTERN = re.compile(
    rf"(?:{'|'.join(_DIARY_SECTION_LABELS)})[：:]"
)
_DIARY_SECTION_PATTERN = re.compile(
    rf"^({'|'.join(_DIARY_SECTION_LABELS)})[：:]\s*(.*)$"
)
_DIARY_SECTION_INLINE_BREAK_PATTERN = re.compile(
    rf"(?<=.)(?=(?:{'|'.join(_DIARY_SECTION_LABELS)})[：:])"
)
# 制度结构强信号：出现则不宜误判为日记
_POLICY_STRUCTURE_PATTERN = re.compile(
    r"(?:第[一二三四五六七八九十百千万零0-9]+[章节篇条]"
    r"|^[一二三四五六七八九十]+[、.．]"
    r"|^\d+[、.．]\s*\S)",
    flags=re.M,
)

CHUNK_PROFILE_AUTO = "auto"
CHUNK_PROFILE_POLICY = "policy"
CHUNK_PROFILE_DIARY = "diary"
SUPPORTED_CHUNK_PROFILES = {CHUNK_PROFILE_AUTO, CHUNK_PROFILE_POLICY, CHUNK_PROFILE_DIARY}


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


def _resolve_title_standalone() -> bool:
    """读取「标题独立成块」开关；读取失败时默认 True。"""

    try:
        from app.core.config import settings

        return settings.chunk_title_standalone
    except Exception:
        return True


# 模块级默认值（与 Settings 一致，便于单测直接断言，无需加载完整配置）。
DEFAULT_CHUNK_SIZE = 256
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_TITLE_STANDALONE = True


def _detect_title(line: str, *, profile: str = CHUNK_PROFILE_POLICY) -> tuple[int, str] | None:
    """识别标题行，返回 (层级, 标题文本)。

    层级越小越“大”：
    - 制度：章(1) > 条(2) > 一、(3) > 1.(4) > 1.1/(一)(5)
    - 日记：日期(1) > 今日反思/金句(2)
    """

    text = line.strip()
    if not text:
        return None

    if profile == CHUNK_PROFILE_DIARY:
        date_match = _DIARY_DATE_PATTERN.match(text)
        if date_match:
            return 1, text
        diary_section = _DIARY_SECTION_PATTERN.match(text)
        if diary_section:
            label = diary_section.group(1)
            return 2, f"{label}："

    markdown_match = _MARKDOWN_TITLE_PATTERN.match(text)
    if markdown_match:
        level = len(markdown_match.group(1))
        title = markdown_match.group(2).strip()
        return (level, title) if title else None

    chapter_match = _CN_CHAPTER_PATTERN.match(text)
    if chapter_match:
        title = f"{chapter_match.group(1)} {chapter_match.group(2)}".strip()
        return 1, title

    article_match = _CN_ARTICLE_PATTERN.match(text)
    if article_match:
        title = f"{article_match.group(1)} {article_match.group(2)}".strip()
        return 2, title

    # 日记模式下不再把「一、/1.」当制度标题，避免误切叙事正文
    if profile == CHUNK_PROFILE_DIARY:
        return None

    cn_item_match = _CN_ITEM_PATTERN.match(text)
    if cn_item_match:
        return 3, text

    digit_item_match = _DIGIT_ITEM_PATTERN.match(text)
    if digit_item_match and len(digit_item_match.group(1)) <= 12:
        # 1. → 4，1.1 → 5；必须深于「一、」(3)，子块才能挂上父块
        level = digit_item_match.group(1).count(".") + 4
        return level, text

    cn_sub_item_match = _CN_SUB_ITEM_PATTERN.match(text)
    if cn_sub_item_match:
        return 5, text

    return None


def detect_chunk_profile(pages: list[dict]) -> str:
    """根据正文特征自动判断切片策略。

    日记识别信号（按强度）：
    1. 强：出现「今日反思/今日金句/今日总结…」标签 → 直接 diary
    2. 中：文首附近有整行日期标题，且几乎无制度结构 → diary
    3. 否则 → policy

    说明：
    - 不再要求「日期 + 反思」同时出现；标签单独即可，避免日期在文本框未抽出时误判。
    - 若同时有明显章/条/一、结构，优先走 policy，防止制度文误入日记。
    """

    merged = "\n".join((page.get("content") or "") for page in pages)
    if not merged.strip():
        return CHUNK_PROFILE_POLICY

    # 先把粘连的日记标签拆到行首，再统计信号
    normalized = _DIARY_SECTION_INLINE_BREAK_PATTERN.sub("\n", merged)
    has_diary_label = bool(_DIARY_SECTION_LABEL_PATTERN.search(normalized))
    has_policy_structure = bool(_POLICY_STRUCTURE_PATTERN.search(normalized))

    # 强信号：日记标签。若同时像制度文，仍以标签为准（标签几乎只出现在日记）
    if has_diary_label:
        return CHUNK_PROFILE_DIARY

    # 中信号：文首 20 行内有整行日期，且没有制度编号结构
    head_lines = normalized.splitlines()[:20]
    has_date_header = any(
        line.strip() and _DIARY_DATE_PATTERN.match(line.strip())
        for line in head_lines
    )
    if has_date_header and not has_policy_structure:
        return CHUNK_PROFILE_DIARY

    # 弱信号：全文仅有散落日期、无制度结构时，不自动升为 diary（避免误伤）
    _ = _DIARY_DATE_LOOSE_PATTERN.search(normalized)
    return CHUNK_PROFILE_POLICY


def _resolve_chunk_profile(pages: list[dict], chunk_profile: str | None) -> str:
    """解析最终切片策略：显式传入优先，否则 auto 探测。"""

    profile = (chunk_profile or CHUNK_PROFILE_AUTO).strip().lower()
    if profile not in SUPPORTED_CHUNK_PROFILES:
        raise ValueError(f"不支持的 chunk_profile: {chunk_profile}")
    if profile == CHUNK_PROFILE_AUTO:
        return detect_chunk_profile(pages)
    return profile


def _is_digit_item_title(text: str) -> bool:
    """是否为「1. / 1.2.」这类数字编号条目（条款下的分点，通常需带上后续说明）。"""

    stripped = text.strip()
    if not stripped:
        return False
    match = _DIGIT_ITEM_PATTERN.match(stripped)
    return bool(match and len(match.group(1)) <= 12)


def _split_cn_item_title_and_body(text: str) -> tuple[str, str | None]:
    """把「一、放假时间 2026年…」拆成短标题 + 正文。

    返回:
        (标题文本, 正文或 None)
    """

    match = _CN_ITEM_TITLE_BODY_PATTERN.match(text.strip())
    if not match:
        return text.strip(), None
    marker, name, body = match.group(1), match.group(2).strip(), match.group(3).strip()
    title = f"{marker}{name}"
    return title, (body or None)


def _split_diary_section_title_and_body(text: str) -> tuple[str, str | None]:
    """把「今日反思：正文…」拆成小节标题 + 正文。"""

    match = _DIARY_SECTION_PATTERN.match(text.strip())
    if not match:
        return text.strip(), None
    label, body = match.group(1), match.group(2).strip()
    return f"{label}：", (body or None)


def _normalize_title_boundaries(content: str, *, profile: str) -> str:
    """在结构化提取前，强制把粘连的章节标题拆到行首。"""

    normalized = _INLINE_TITLE_BREAK_PATTERN.sub(r"\1\n\2", content)
    normalized = _FORCE_BREAK_BEFORE_SECTION_PATTERN.sub("\n", normalized)
    # 日记标签无论当前策略都先断行，避免埋在段中无法识别
    normalized = _DIARY_SECTION_INLINE_BREAK_PATTERN.sub("\n", normalized)
    return normalized


def _extract_structured_blocks(content: str, *, profile: str = CHUNK_PROFILE_POLICY) -> list[dict]:
    """从原始文本中提取结构化块（标题块/段落块）。"""

    normalized_content = _normalize_title_boundaries(content, profile=profile)

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

    def append_title(level: int, title_text: str) -> None:
        nonlocal section_level, section_title
        flush_paragraph()
        section_level, section_title = level, title_text
        blocks.append({
            "text": title_text,
            "boundary_type": "title",
            "section_title": section_title,
            "section_level": section_level,
            "paragraph_index": None,
        })

    for raw_line in normalized_content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue

        title = _detect_title(stripped, profile=profile)
        if title:
            level, _ = title
            if profile == CHUNK_PROFILE_DIARY and level == 2 and _DIARY_SECTION_PATTERN.match(stripped):
                short_title, body = _split_diary_section_title_and_body(stripped)
                append_title(level, short_title)
                if body:
                    paragraph_lines.append(body)
                    flush_paragraph()
                continue

            # 「一、放假时间 2026年…」拆成父标题 + 子正文，避免大标题吞掉整段
            if (
                profile != CHUNK_PROFILE_DIARY
                and level == 3
                and _CN_ITEM_PATTERN.match(stripped)
                and not _is_digit_item_title(stripped)
            ):
                short_title, body = _split_cn_item_title_and_body(stripped)
                append_title(level, short_title)
                if body:
                    paragraph_lines.append(body)
                    flush_paragraph()
                continue

            append_title(level, stripped)
            continue

        paragraph_lines.append(stripped)
        # 日记正文按行/段切开，便于后续单段分析；制度文仍合并连续行成段
        if profile == CHUNK_PROFILE_DIARY:
            flush_paragraph()

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


def _collect_digit_body(structured_blocks: list[dict], start_index: int) -> tuple[list[str], int]:
    """收集数字分点标题后的从属正文（到下一标题前），返回 (正文片段, 下一未消费下标)。"""

    parts: list[str] = []
    cursor = start_index + 1
    while cursor < len(structured_blocks):
        nxt = structured_blocks[cursor]
        if nxt["boundary_type"] == "title":
            break
        parts.append(nxt["text"])
        cursor += 1
    return parts, cursor


def split_pages_to_chunks(
    pages: list[dict],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    title_standalone: bool | None = None,
    chunk_profile: str | None = None,
) -> list[dict]:
    """将解析后的页列表按结构化规则切成文本块。

    参数:
        pages: 页列表，每项形如 ``{"page_number": int|None, "content": str}``。
        chunk_size: 单块最大字符数；传 None 时取配置或模块默认 256。
        chunk_overlap: 相邻块重叠字符数；传 None 时取配置或模块默认 50。
        title_standalone: True 时启用层级父子块（默认）；False 时退化为扁平合并。
        chunk_profile: 切片策略 ``auto`` / ``policy`` / ``diary``；默认 auto 自动识别。

    返回:
        切片列表，每项形如::

            {
                "content": str,
                "page_number": int|None,
                "chunk_index": int,
                "parent_chunk_index": int|None,  # 子块指向父块 chunk_index；入库后解析为 parent_chunk_id
                "metadata": dict,                # 含 chunk_profile / section_level 等
            }

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

    if title_standalone is None:
        title_standalone = _resolve_title_standalone()

    resolved_profile = _resolve_chunk_profile(pages, chunk_profile)

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
        structured_blocks = _extract_structured_blocks(content, profile=resolved_profile)
        current_chunk = ""
        current_meta: dict | None = None
        current_parent_index: int | None = None
        # 层级栈：(section_level, chunk_index)，用于给子块挂 parent_chunk_index
        parent_stack: list[tuple[int, int]] = []

        def resolve_parent_index(level: int) -> int | None:
            """弹出同级/更深标题后，返回最近更高级标题的 chunk_index。"""

            while parent_stack and parent_stack[-1][0] >= level:
                parent_stack.pop()
            return parent_stack[-1][1] if parent_stack else None

        def flush_current_chunk() -> None:
            nonlocal current_chunk, current_meta
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

            emit_chunk(chunk_text, current_meta, current_parent_index)
            current_chunk = ""
            current_meta = None

        def emit_chunk(
            content_text: str,
            meta: dict | None,
            parent_idx: int | None,
        ) -> int | None:
            """写入一条切片，返回新块的 chunk_index；与上一条内容完全相同则跳过。"""

            nonlocal chunk_index
            content_text = content_text.strip()
            if not content_text:
                return None

            last_content = chunks[-1]["content"] if chunks else None
            if content_text == last_content:
                return None

            chunk_meta = dict(meta) if meta else {}
            chunk_meta["chunk_profile"] = resolved_profile
            if parent_idx is not None:
                chunk_meta["parent_chunk_index"] = parent_idx

            chunk_item = {
                "content": content_text,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "parent_chunk_index": parent_idx,
            }
            if chunk_meta:
                chunk_item["metadata"] = chunk_meta
            chunks.append(chunk_item)
            emitted_index = chunk_index
            chunk_index += 1
            return emitted_index

        def emit_text_pieces(
            text: str,
            base_meta: dict,
            parent_idx: int | None,
        ) -> int | None:
            """按长度落盘文本；返回最后一块的 chunk_index。"""

            last_emitted: int | None = None
            if len(text) <= chunk_size:
                return emit_chunk(text, base_meta, parent_idx)

            for piece in _split_long_text(text, chunk_size, chunk_overlap, base_meta):
                emitted = emit_chunk(piece["content"], piece["metadata"], parent_idx)
                if emitted is not None:
                    last_emitted = emitted
            return last_emitted

        def emit_hierarchical_title(title_text: str, title_meta: dict, start_index: int) -> int:
            """大标题独立成块；数字分点可带正文；子块写入 parent_chunk_index。"""

            nonlocal current_parent_index
            level = int(title_meta.get("section_level") or 99)
            parent_idx = resolve_parent_index(level)
            meta = dict(title_meta)

            # 数字分点：标题 + 从属正文同块（叶节点），挂到上级大标题
            if resolved_profile != CHUNK_PROFILE_DIARY and _is_digit_item_title(title_text):
                body_parts, cursor = _collect_digit_body(structured_blocks, start_index)
                parts = [title_text.strip(), *body_parts]
                merged = "\n".join(part for part in parts if part)
                if len(parts) > 1:
                    meta["boundary_type"] = "title_with_body"
                emitted = emit_text_pieces(merged, meta, parent_idx)
                if emitted is not None:
                    parent_stack.append((level, emitted))
                    current_parent_index = emitted
                return cursor

            # 章/条/日期/今日小节等：标题单独成父块，正文留给后续子块
            meta["boundary_type"] = "title"
            emitted = emit_chunk(title_text.strip(), meta, parent_idx)
            if emitted is not None:
                parent_stack.append((level, emitted))
                current_parent_index = emitted
            return start_index + 1

        block_index = 0
        while block_index < len(structured_blocks):
            block = structured_blocks[block_index]
            block_text = block["text"]
            block_meta = {
                "boundary_type": block["boundary_type"],
                "section_title": block.get("section_title"),
                "section_level": block.get("section_level"),
                "paragraph_index": block.get("paragraph_index"),
            }

            if block["boundary_type"] == "title":
                flush_current_chunk()
                if title_standalone:
                    block_index = emit_hierarchical_title(block_text, block_meta, block_index)
                    continue

                # title_standalone=False：扁平合并，不写父子关系
                current_parent_index = None

            parent_idx = None
            if title_standalone and parent_stack:
                parent_idx = parent_stack[-1][1]

            if len(block_text) > chunk_size:
                flush_current_chunk()
                emit_text_pieces(block_text, block_meta, parent_idx)
                block_index += 1
                continue

            if title_standalone:
                # 层级模式：段落直接作为当前父标题的子块落盘，避免并入标题正文
                flush_current_chunk()
                child_meta = dict(block_meta)
                child_meta["boundary_type"] = "child_paragraph"
                # 日记正文按段落落块，便于后续对单段做情绪/分析；超长段再滑窗
                if resolved_profile == CHUNK_PROFILE_DIARY:
                    child_meta["boundary_type"] = "diary_paragraph"
                    emit_text_pieces(block_text, child_meta, parent_idx)
                    block_index += 1
                    continue

                emit_chunk(block_text, child_meta, parent_idx)
                block_index += 1
                continue

            candidate = block_text if not current_chunk else f"{current_chunk}\n{block_text}"
            if len(candidate) <= chunk_size:
                current_chunk = candidate
                if current_meta is None:
                    current_meta = dict(block_meta)
                else:
                    current_meta["boundary_type"] = "paragraph_pack"
                block_index += 1
                continue

            flush_current_chunk()
            current_chunk = block_text
            current_meta = dict(block_meta)
            block_index += 1

        flush_current_chunk()

    return chunks


# 兼容旧调用名；新代码请优先使用 split_pages_to_chunks。
split_text = split_pages_to_chunks
