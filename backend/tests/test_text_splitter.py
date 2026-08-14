"""文本切片服务单测。

覆盖：默认 256/50、页内滑动窗口、跨页全局序号、空页跳过、兼容别名。
"""

import unittest

from app.services.text_splitter import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TITLE_STANDALONE,
    detect_chunk_profile,
    split_pages_to_chunks,
    split_text,
)


class TextSplitterTests(unittest.TestCase):
    def test_default_chunk_params_for_qa_scene(self):
        """精准问答场景模块默认切分参数应为 256/50，标题默认独立成块。"""

        self.assertEqual(DEFAULT_CHUNK_SIZE, 256)
        self.assertEqual(DEFAULT_CHUNK_OVERLAP, 50)
        self.assertTrue(DEFAULT_TITLE_STANDALONE)

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

    def test_inline_title_should_start_new_chunk(self):
        """内联标题（紧跟句号）应切到下一块，避免粘在上一个切片尾部。"""

        pages = [{
            "page_number": 1,
            "content": (
                "（5）上传附件：病假必须上传正规医院诊断证明、病历、病假条等佐证材料，无附件不予审批。"
                "3. 所有信息填写核对无误后，提交申请，系统将自动推送至对应审批人待审。"
                "二、审批路径说明结合公司请假管理制度及岗位层级，统一审批流转路径如下："
                "三、请假时长计算规则为规范假期核算、统一考勤标准，公司请假时长计算规则如下："
            ),
        }]

        chunks = split_pages_to_chunks(pages, chunk_size=120, chunk_overlap=20, title_standalone=True)
        self.assertGreaterEqual(len(chunks), 2)

        joined = [item["content"] for item in chunks]
        # “三、请假时长计算规则”必须出现在新块开头附近，而不是上一块尾部。
        idx = next(i for i, text in enumerate(joined) if "三、请假时长计算规则" in text)
        self.assertGreater(idx, 0)
        self.assertNotIn("三、请假时长计算规则", joined[idx - 1])

    def test_title_standalone_emits_title_only_chunk(self):
        """开启 title_standalone 时，标题应单独成块，正文进入下一块。"""

        pages = [{
            "page_number": 1,
            "content": (
                "二、审批路径说明\n"
                "结合公司请假管理制度及岗位层级，统一审批流转路径如下：\n"
                "三、请假时长计算规则\n"
                "为规范假期核算、统一考勤标准，公司请假时长计算规则如下："
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50, title_standalone=True)

        title_chunks = [
            item for item in chunks
            if item.get("metadata", {}).get("boundary_type") == "title"
        ]
        self.assertGreaterEqual(len(title_chunks), 2)
        self.assertEqual(title_chunks[0]["content"], "二、审批路径说明")
        self.assertEqual(title_chunks[1]["content"], "三、请假时长计算规则")
        self.assertTrue(any("统一审批流转路径如下" in item["content"] for item in chunks))
        self.assertTrue(any("公司请假时长计算规则如下" in item["content"] for item in chunks))

    def test_title_standalone_off_allows_merge_within_size(self):
        """关闭 title_standalone 时，标题可与后续短段落合并（在 chunk_size 内）。"""

        pages = [{
            "page_number": 1,
            "content": "二、审批路径说明\n结合公司制度执行。",
        }]
        standalone_chunks = split_pages_to_chunks(
            pages, chunk_size=256, chunk_overlap=50, title_standalone=True,
        )
        merged_chunks = split_pages_to_chunks(
            pages, chunk_size=256, chunk_overlap=50, title_standalone=False,
        )

        self.assertGreaterEqual(len(standalone_chunks), 2)
        self.assertEqual(len(merged_chunks), 1)
        self.assertIn("二、审批路径说明", merged_chunks[0]["content"])
        self.assertIn("结合公司制度执行", merged_chunks[0]["content"])

    def test_digit_item_keeps_following_bullet_list_together(self):
        """数字编号条目应与紧随其后的子列表同块，避免「1. 申请」与「- 事假…」拆开。"""

        pages = [{
            "page_number": None,
            "content": (
                "第十五条 请假流程\n"
                "1. 申请：员工须提前填写《请假申请单》，注明请假类别、起止时间、事由等。\n"
                "- 事假须至少提前1天申请；\n"
                "- 年休假须提前3天申请；\n"
                "- 婚假、产假须提前15天申请；\n"
                "- 病假、工伤假、丧假等突发情况可事后补办手续，但须在返岗后第一个工作日内补齐。\n"
                "2. 审批：按审批权限逐级审批。\n"
                "3. 备案：审批完成后，《请假申请单》由人力资源部门存档。"
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50, title_standalone=True)

        article = next(item for item in chunks if item["content"].strip() == "第十五条 请假流程")
        apply_chunks = [item for item in chunks if "1. 申请" in item["content"]]
        self.assertEqual(len(apply_chunks), 1)
        apply_text = apply_chunks[0]["content"]
        self.assertIn("事假须至少提前1天申请", apply_text)
        self.assertIn("年休假须提前3天申请", apply_text)
        self.assertIn("返岗后第一个工作日内补齐", apply_text)
        self.assertNotIn("2. 审批", apply_text)
        self.assertEqual(apply_chunks[0].get("parent_chunk_index"), article["chunk_index"])

        self.assertTrue(any(item["content"].startswith("2. 审批") for item in chunks))
        self.assertTrue(any(item["content"].startswith("3. 备案") for item in chunks))

    def test_hierarchy_stops_digit_item_before_next_article(self):
        """层级切分：数字分点不得吞并后续「第X条」；子块挂父块 index。"""

        pages = [{
            "page_number": None,
            "content": (
                "第四章 请假流程\n"
                "第十五条 请假流程\n"
                "4. 销假：请假结束返岗后，须在当天向直属主管销假，并在系统中确认销假状态。\n"
                "第十六条 请假期间的交接\n"
                "员工请假超过3天的，须完成工作交接并指定代理人，交接内容应书面确认。\n"
                "第五章 违纪处理\n"
                "第十七条 以下情形按旷工处理："
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50, title_standalone=True)
        by_content = {item["content"]: item for item in chunks}

        chapter4 = by_content["第四章 请假流程"]
        article15 = by_content["第十五条 请假流程"]
        cancel = next(item for item in chunks if item["content"].startswith("4. 销假"))
        article16 = by_content["第十六条 请假期间的交接"]
        body16 = next(item for item in chunks if "工作交接" in item["content"])
        chapter5 = by_content["第五章 违纪处理"]

        self.assertIsNone(chapter4.get("parent_chunk_index"))
        self.assertEqual(article15.get("parent_chunk_index"), chapter4["chunk_index"])
        self.assertEqual(cancel.get("parent_chunk_index"), article15["chunk_index"])
        self.assertNotIn("第十六条", cancel["content"])
        self.assertEqual(article16.get("parent_chunk_index"), chapter4["chunk_index"])
        self.assertEqual(body16.get("parent_chunk_index"), article16["chunk_index"])
        self.assertIsNone(chapter5.get("parent_chunk_index"))
        self.assertTrue(any("第十七条" in item["content"] for item in chunks))

        self.assertEqual(chapter4["metadata"].get("section_level"), 1)
        self.assertEqual(article15["metadata"].get("section_level"), 2)
        self.assertEqual(cancel["metadata"].get("section_level"), 4)

    def test_notice_cn_item_parents_digit_children(self):
        """通知类文档：一/二拆开；1/2/3 挂在对应「三、」「四、」父块下。"""

        pages = [{
            "page_number": 1,
            "content": (
                "关于2026年春节放假及调休安排的通知\n"
                "全体员工：\n"
                "根据国务院办公厅通知精神，现将有关事项通知如下一、放假时间 "
                "2026年2月14日至2月22日放假，共计9天，2月23日（星期一）正常上班。"
                "二、调休安排 2月7日（周六）、2月28日（周六）为正常上班日。"
                "三、请假衔接说明\n"
                "1. 如需提前离岗请走OA申请。\n"
                "2. 事假期间不计薪。\n"
                "3. 假期值班由综合管理部统筹。\n"
                "四、温馨提示\n"
                "1. 负责人确认放假去向。\n"
                "2. 保持手机畅通。\n"
                "3. 返岗首日按时打卡。"
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50, title_standalone=True)
        by_title = {
            item["content"]: item for item in chunks
            if item["content"] in {
                "一、放假时间", "二、调休安排", "三、请假衔接说明", "四、温馨提示",
            }
        }

        self.assertIn("一、放假时间", by_title)
        self.assertIn("二、调休安排", by_title)
        merged = next(
            (
                item for item in chunks
                if "一、放假时间" in item["content"] and "二、调休安排" in item["content"]
            ),
            None,
        )
        self.assertIsNone(merged)

        section3 = by_title["三、请假衔接说明"]
        section4 = by_title["四、温馨提示"]
        children3 = [item for item in chunks if item.get("parent_chunk_index") == section3["chunk_index"]]
        children4 = [item for item in chunks if item.get("parent_chunk_index") == section4["chunk_index"]]
        self.assertTrue(any(item["content"].startswith("1.") for item in children3))
        self.assertTrue(any(item["content"].startswith("2.") for item in children3))
        self.assertTrue(any(item["content"].startswith("3.") for item in children3))
        self.assertTrue(any(item["content"].startswith("1.") for item in children4))

        body1 = next(item for item in chunks if "2月14日至2月22日" in item["content"])
        self.assertEqual(body1.get("parent_chunk_index"), by_title["一、放假时间"]["chunk_index"])

    def test_detect_chunk_profile_diary_vs_policy(self):
        """日记标签为强信号；制度编号为 policy；仅日期且无制度结构也可 diary。"""

        diary_with_label = [{
            "page_number": 1,
            "content": (
                "能好好工作、好好生活，也是一种幸运。\n"
                "今日反思：想做的事情太多。\n"
                "今日金句：慢慢来，一件一件实现。"
            ),
        }]
        diary_date_only = [{
            "page_number": 1,
            "content": "2026年7月17日（周五）\n今天心情一般，随便写两句。\n明天继续。",
        }]
        policy_pages = [{
            "page_number": 1,
            "content": "第三章 请假审批权限\n第十三条 审批权限\n1. 申请：提交表单",
        }]
        self.assertEqual(detect_chunk_profile(diary_with_label), "diary")
        self.assertEqual(detect_chunk_profile(diary_date_only), "diary")
        self.assertEqual(detect_chunk_profile(policy_pages), "policy")

    def test_diary_sections_split_without_date_header(self):
        """无日期行但含今日反思/金句时，也应按日记切开，避免并进同一正文块。"""

        pages = [{
            "page_number": None,
            "content": (
                "我已经开始幻想拿一个月的赔偿金出去玩一圈。\n"
                "当然，这些目前也只是一个美好的夙愿。\n"
                "能不被裁员当然最好，能好好工作、好好生活，也是一种幸运。\n"
                "今日反思：\n"
                "我意识到，我的问题可能不是没有精力，而是想做的事情太多。\n"
                "和之前相比，我开始明白，真正的坚持不一定来自强迫自己。\n"
                "人生还有很多想去的地方、想做的事情，不必急着一次完成。\n"
                "今日金句：\n"
                "想做的事情很多没关系，人生还有很长，慢慢来，一件一件实现。"
            ),
        }]
        self.assertEqual(detect_chunk_profile(pages), "diary")
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50, chunk_profile="auto")

        reflection = next(item for item in chunks if item["content"].strip() == "今日反思：")
        golden = next(item for item in chunks if item["content"].strip() == "今日金句：")
        self.assertTrue(any("我意识到，我的问题可能不是没有精力" in item["content"] for item in chunks))
        self.assertTrue(any("想做的事情很多没关系" in item["content"] for item in chunks))

        # 反思/金句不得仍埋在同一大段正文里
        for item in chunks:
            if "当然，这些目前也只是一个美好的夙愿" in item["content"]:
                self.assertNotIn("今日反思", item["content"])
                self.assertNotIn("今日金句", item["content"])

        reflection_children = [
            item for item in chunks
            if item.get("parent_chunk_index") == reflection["chunk_index"]
        ]
        golden_children = [
            item for item in chunks
            if item.get("parent_chunk_index") == golden["chunk_index"]
        ]
        self.assertGreaterEqual(len(reflection_children), 1)
        self.assertGreaterEqual(len(golden_children), 1)

    def test_diary_profile_chunks_under_date_parent(self):
        """日记：日期为父块；正文/反思/金句挂在日期或小节下。"""

        pages = [{
            "page_number": 1,
            "content": (
                "2026 年 7 月 17 日 | 周五\n"
                "今天我去见了一个人，聊了很多。\n"
                "回来后觉得表达欲和表达能力不是一回事。\n"
                "今日反思：说话之前先想清楚自己真正想表达什么，而不是急着证明自己。\n"
                "今日金句：表达欲，不等于表达能力。"
            ),
        }]
        chunks = split_pages_to_chunks(pages, chunk_size=256, chunk_overlap=50, chunk_profile="auto")
        self.assertTrue(all(item["metadata"].get("chunk_profile") == "diary" for item in chunks))

        date_chunk = next(item for item in chunks if "2026" in item["content"] and "周五" in item["content"])
        self.assertIsNone(date_chunk.get("parent_chunk_index"))
        self.assertEqual(date_chunk["metadata"].get("section_level"), 1)

        body_chunks = [
            item for item in chunks
            if item.get("parent_chunk_index") == date_chunk["chunk_index"]
            and not item["content"].startswith("今日")
        ]
        # 正文按段落切开，至少两段叙事各自成块
        self.assertGreaterEqual(len(body_chunks), 2)
        self.assertTrue(any("今天我去见了一个人" in item["content"] for item in body_chunks))
        self.assertTrue(any("表达欲和表达能力不是一回事" in item["content"] for item in body_chunks))
        self.assertTrue(
            all(item["metadata"].get("boundary_type") == "diary_paragraph" for item in body_chunks)
        )

        reflection = next(item for item in chunks if item["content"].startswith("今日反思"))
        golden = next(item for item in chunks if item["content"].startswith("今日金句"))
        self.assertEqual(reflection.get("parent_chunk_index"), date_chunk["chunk_index"])
        self.assertEqual(golden.get("parent_chunk_index"), date_chunk["chunk_index"])

        reflection_body = [
            item for item in chunks
            if item.get("parent_chunk_index") == reflection["chunk_index"]
        ]
        self.assertTrue(any("说话之前先想清楚" in item["content"] for item in reflection_body))


if __name__ == "__main__":
    unittest.main()
