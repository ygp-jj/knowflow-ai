"""文本切片服务单测。"""

import unittest

from app.services.text_splitter import split_text


class TextSplitterTests(unittest.TestCase):
    def test_split_short_text_single_chunk(self):
        pages = [{"page_number": None, "content": "短文本"}]
        chunks = split_text(pages, chunk_size=800, chunk_overlap=120)

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
        chunks = split_text(pages)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 2)


if __name__ == "__main__":
    unittest.main()
