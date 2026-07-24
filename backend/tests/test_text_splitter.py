"""文本切片服务单测。"""

import unittest

from app.services.text_splitter import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, split_text


class TextSplitterTests(unittest.TestCase):
    def test_default_chunk_params_for_qa_scene(self):
        """精准问答场景默认切分为 256/50。"""

        self.assertEqual(DEFAULT_CHUNK_SIZE, 256)
        self.assertEqual(DEFAULT_CHUNK_OVERLAP, 50)

    def test_split_short_text_single_chunk(self):
        pages = [{"page_number": None, "content": "短文本"}]
        chunks = split_text(pages, chunk_size=256, chunk_overlap=50)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[0]["content"], "短文本")

    def test_split_with_overlap_and_multi_page(self):
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
        pages = [
            {"page_number": 1, "content": "   "},
            {"page_number": 2, "content": "有效内容"},
        ]
        chunks = split_text(pages, chunk_size=256, chunk_overlap=50)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 2)

    def test_requirement_window_example(self):
        """约束文档示例：chunk_size=8, overlap=3。"""

        pages = [{"page_number": 1, "content": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}]
        chunks = split_text(pages, chunk_size=8, chunk_overlap=3)

        self.assertEqual(
            [item["content"] for item in chunks],
            ["ABCDEFGH", "FGHIJKLM", "KLMNOPQR", "PQRSTUVW", "UVWXYZ"],
        )
        self.assertEqual([item["chunk_index"] for item in chunks], [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
