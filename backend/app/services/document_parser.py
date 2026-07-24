"""文档解析服务：将上传文件转换为带页码的纯文本页列表。"""

from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


class UnsupportedDocumentTypeError(ValueError):
    """不支持的文档类型异常。"""


def parse_document(file_path: str) -> list[dict]:
    """按扩展名分发解析，返回 ``[{page_number, content}, ...]``。

    参数:
        file_path: 本地临时文件路径。
    """

    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(file_path)

    if suffix in {".docx", ".doc"}:
        return parse_docx(file_path)

    if suffix in {".md", ".txt", ".markdown"}:
        return parse_text(file_path)

    raise UnsupportedDocumentTypeError(f"暂不支持解析的文件类型: {suffix or '(无扩展名)'}")


def parse_pdf(file_path: str) -> list[dict]:
    """解析 PDF，按页提取文本。"""

    reader = PdfReader(file_path)
    pages = []

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({
            "page_number": index + 1,
            "content": text,
        })

    return pages


def parse_docx(file_path: str) -> list[dict]:
    """解析 Word 文档，拼接非空段落。"""

    document = DocxDocument(file_path)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    return [{"page_number": None, "content": text}]


def parse_text(file_path: str) -> list[dict]:
    """解析 TXT / Markdown 纯文本文件。"""

    text = Path(file_path).read_text(encoding="utf-8")
    return [{"page_number": None, "content": text}]
