"""文本切片服务单测。

覆盖：默认 256/50、页内滑动窗口、跨页全局序号、空页跳过。
"""

import unittest

from app.services.text_splitter import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, split_text


class TextSplitterTests(unittest.TestCase):
    def test_default_chunk_params_for_qa_scene(self):
        """精准问答场景模块默认切分参数应为 256/50。"""

        self.assertEqual(DEFAULT_CHUNK_SIZE, 256)
        self.assertEqual(DEFAULT_CHUNK_OVERLAP, 50)

    def test_split_short_text_single_chunk(self):
        """短于窗口的文本应只产出一块，且 chunk_index 从 0 开始。"""

        pages = [{"page_number": None, "content": "短文本"}]
        chunks = split_text(pages, chunk_size=256, chunk_overlap=50)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[0]["content"], "短文本")

    def test_split_with_overlap_and_multi_page(self):
        """多页切分时 chunk_index 应跨页连续，且保留各自 page_number。"""

        pages = [
            {"page_number": 1, "content": "a" * 20},
            {"page_number": 2, "content": "b" * 15},
        ]
        chunks = split_text(pages, chunk_size=10, chunk_overlap=2)

        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["page_number"], 1)
        self.assertEqual(chunks[-1]["page_number"], 2)
        self.assertEqual([item["chunk_index"] for item in chunks], list(range(len(chunks))))

    def test_skip_empty_pages(self):
        """仅空白的页应被跳过，不产生切片。"""

        pages = [
            {"page_number": 1, "content": "   "},
            {"page_number": 2, "content": "有效内容"},
        ]
        chunks = split_text(pages, chunk_size=256, chunk_overlap=50)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 2)

    def test_requirement_window_example(self):
        """页内滑动窗口示例：chunk_size=8、overlap=3 时步进为 5。"""

        pages = [{"page_number": 1, "content": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}]
        chunks = split_text(pages, chunk_size=8, chunk_overlap=3)

        self.assertEqual(
            [item["content"] for item in chunks],
            ["ABCDEFGH", "FGHIJKLM", "KLMNOPQR", "PQRSTUVW", "UVWXYZ"],
        )
        self.assertEqual([item["chunk_index"] for item in chunks], [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
