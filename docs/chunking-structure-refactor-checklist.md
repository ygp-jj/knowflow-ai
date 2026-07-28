# 文档切片结构化改造清单（可执行）

> 目标：从“纯字符滑窗”升级到“标题/段落优先，句子/滑窗兜底”，减少重复与断句。

## 已完成（本次已落地到 dev）

- [x] `text_splitter.py` 增加标题识别规则（Markdown / 中文章节 / 编号条款）。
- [x] 先抽取结构化块（title / paragraph），再组装 chunk。
- [x] 超长段落走句子拆分，单句过长再滑窗兜底。
- [x] 保留兼容入口：`split_text = split_pages_to_chunks`。
- [x] 在 chunk `metadata` 中写入结构信息：
  - `boundary_type`（title/paragraph/paragraph_pack/sentence/sliding）
  - `section_title`
  - `section_level`
  - `paragraph_index`
- [x] **标题独立成块开关**（`CHUNK_TITLE_STANDALONE`，默认 `true`）
  - `true`：每个标题单独一个 chunk，不与后续段落合并
  - `false`：标题可与后续短段落合并（在 `chunk_size` 内）
- [x] 单测补齐：
  - 标题+段落优先切分
  - 长段落 sentence/sliding 兜底
  - 现有行为回归（默认参数、空页跳过、别名兼容）

## 下一步（建议按顺序执行）

### Phase 2：规则精细化

- [ ] 将标题 regex 提取为配置项（便于按业务文档类型微调）。
- [ ] 增加“短段合并阈值”配置（避免碎片化 chunk）。
- [x] 增加“标题独立成块”开关（`CHUNK_TITLE_STANDALONE`，默认 true）。
- [ ] 增加表格/列表专用边界处理（避免条款跨行混排）。

### Phase 3：数据与接口增强

- [ ] `DocumentChunkRead` 增加 `metadata` 返回（前端可展示章节来源）。
- [ ] 文档切片列表页展示 `section_title` 与 `boundary_type`。
- [ ] 增加回放接口（按 `section_title` 聚合查看 chunks）。

### Phase 4：检索质量验证

- [ ] 制作 20~50 条真实问答集（命中具体制度条款）。
- [ ] 对比改造前后 Top-3 命中率与答案引用完整性。
- [ ] 记录“重复块率 / 断句率 / 平均 chunk token”指标。

## 验证命令

```bash
cd backend
PYTHONPATH=. python3 -m unittest tests.test_text_splitter -v
```

