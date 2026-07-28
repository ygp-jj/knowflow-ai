"""文本切片服务单测。

覆盖：默认 256/50、页内滑动窗口、跨页全局序号、空页跳过、兼容别名。
"""

import unittest

from app.services.text_splitter import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    split_pages_to_chunks,
    split_text,
)


class TextSplitterTests(unittest.TestCase):
    def test_default_chunk_params_for_qa_scene(self):
        """精准问答场景模块默认切分参数应为 256/50。"""

        self.assertEqual(DEFAULT_CHUNK_SIZE, 256)
        self.assertEqual(DEFAULT_CHUNK_OVERLAP, 50)

    def test_split_short_text_single_chunk(self):
        """短于窗口的文本应只产出一块，且 chunk_index 从 0 开始。"""

        pages = [{"page_number": None, "content": "短文本"}]
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[0]["content"], "短文本")

    def test_split_with_overlap_and_multi_page(self):
        """多页切分时 chunk_index 应跨页连续，且保留各自 page_number。"""

        pages = [
            {"page_number": 1, "content": "a" * 20},
            {"page_number": 2, "content": "b" * 15},
        ]
        chunks = split_pages_to_chunks(pages, chunk_size=10, chunk_overlap=2)

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
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 2)

    def test_requirement_window_example(self):
        """页内滑动窗口示例：chunk_size=8、overlap=3 时步进为 5。"""

        pages = [{"page_number": 1, "content": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}]
        chunks = split_pages_to_chunks(pages, chunk_size=8, chunk_overlap=3)

        self.assertEqual(
            [item["content"] for item in chunks],
            ["ABCDEFGH", "FGHIJKLM", "KLMNOPQR", "PQRSTUVW", "UVWXYZ"],
        )
        self.assertEqual([item["chunk_index"] for item in chunks], [0, 1, 2, 3, 4])

    def test_align_chunk_boundary_avoids_mid_word_prefix(self):
        """切片应尽量在标点/换行边界衔接，避免下一片从词中间开头。"""

        pages = [{
            "page_number": 1,
            "content": (
                "附件：病假必须上传正规医院诊断证明、病历、病假条等佐证材料，无附件不予审批。\n"
                "所有信息填写核对无误后，提交申请。"
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=40, chunk_overlap=12)

        self.assertGreaterEqual(len(chunks), 2)
        for item in chunks[1:]:
            self.assertFalse(item["content"].startswith("件："))
        self.assertTrue(any("无附件不予审批" in item["content"] for item in chunks))
        self.assertTrue(any("所有信息填写核对无误后" in item["content"] for item in chunks))

    def test_split_text_alias_matches_formal_api(self):
        """兼容别名 split_text 应与正式入口行为一致。"""

        pages = [{"page_number": 1, "content": "abcdefghij"}]
        formal = split_pages_to_chunks(pages, chunk_size=4, chunk_overlap=1)
        alias = split_text(pages, chunk_size=4, chunk_overlap=1)
        self.assertEqual(formal, alias)
        self.assertIs(split_text, split_pages_to_chunks)

    def test_title_and_paragraph_first_chunking(self):
        """应优先按标题/段落切分，并在 metadata 中保留结构信息。"""

        pages = [{
            "page_number": 1,
            "content": (
                "一、请假申请流程\n"
                "员工需登录系统提交申请，并上传证明材料。\n\n"
                "二、审批规则\n"
                "直属主管 1 个工作日内审批。"
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=40, chunk_overlap=10)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(any(item["metadata"].get("section_title") == "一、请假申请流程" for item in chunks))
        self.assertTrue(any(item["metadata"].get("section_title") == "二、审批规则" for item in chunks))
        self.assertTrue(any("直属主管 1 个工作日内审批" in item["content"] for item in chunks))

    def test_long_paragraph_uses_sentence_or_sliding_fallback(self):
        """超长段落应触发 sentence/sliding 兜底，并保留结构元数据。"""

        pages = [{
            "page_number": 1,
            "content": (
                "三、补充说明\n"
                "本制度适用于全体员工。"
                "请严格遵循流程提交申请。"
                "若材料不全，系统会驳回并提示补充。"
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=24, chunk_overlap=8)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all("metadata" in item for item in chunks))
        self.assertTrue(any(item["metadata"]["boundary_type"] in {"sentence", "sliding"} for item in chunks))


if __name__ == "__main__":
    unittest.main()
