"""文档解析服务单测。"""

import tempfile
import unittest
from pathlib import Path

from docx import Document as DocxDocument

from app.services.document_parser import UnsupportedDocumentTypeError, parse_document, parse_text


class DocumentParserTests(unittest.TestCase):
    def test_parse_text_and_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            txt_path = Path(temp_dir) / "note.txt"
            md_path = Path(temp_dir) / "note.md"
            txt_path.write_text("hello txt", encoding="utf-8")
            md_path.write_text("# hello md", encoding="utf-8")

            self.assertEqual(parse_text(str(txt_path)), [{"page_number": None, "content": "hello txt"}])
            self.assertEqual(
                parse_document(str(md_path)),
                [{"page_number": None, "content": "# hello md"}],
            )

    def test_parse_docx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "demo.docx"
            document = DocxDocument()
            document.add_paragraph("第一段")
            document.add_paragraph("第二段")
            document.save(docx_path)

            pages = parse_document(str(docx_path))
            self.assertEqual(len(pages), 1)
            self.assertIsNone(pages[0]["page_number"])
            self.assertIn("第一段", pages[0]["content"])
            self.assertIn("第二段", pages[0]["content"])

    def test_unsupported_xlsx_raises(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            xlsx_path = Path(temp_dir) / "sheet.xlsx"
            xlsx_path.write_bytes(b"not-a-real-xlsx")

            with self.assertRaises(UnsupportedDocumentTypeError) as ctx:
                parse_document(str(xlsx_path))

            self.assertIn("暂不支持", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
