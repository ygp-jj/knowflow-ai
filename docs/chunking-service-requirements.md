# 文档切分服务需求说明（v1.1）

> 状态：已确认采纳  
> 关联决策：A（不启用前端轮询）+ B（最终状态统一为 `embedded`）+ C（维持现有 API 路径风格）

---

## 1. 产品场景（已确认）

| 项 | 结论 |
|----|------|
| 场景 | 企业内部知识库问答 / 客服辅助 |
| 文档类型 | 以非结构化文本为主（PDF/Word/TXT/MD） |
| 规模 | 数百级文档即可 |
| 召回 | Top-3 |
| Embedding | 模型待定；切分参数按常见中文 Embedding 经验默认 |

---

## 2. 切分算法约束

1. **按页滑动窗口**：在单页文本上按 `chunk_size` / `chunk_overlap` 滑动切分，**不是**「一页一块」。
2. **空页跳过**：某页抽取文本为空（含仅空白）时不产生 chunk。
3. **全局序号**：`chunk_index` 从 0 起，按产出顺序递增，跨页连续。
4. **默认参数**：`chunk_size=256`，`chunk_overlap=50`；可通过环境变量 `CHUNK_SIZE` / `CHUNK_OVERLAP` 覆盖。
5. **可配置**：后续支持按知识库/文档覆盖切分参数（当前实现为全局配置）。

实现入口：`backend/app/services/text_splitter.py` 的 `split_pages_to_chunks`
（兼容别名 `split_text`，行为相同）。

---

## 3. 状态机（含向量化终态）

```
uploaded → parsing → chunking → chunked → embedding → embedded
                ↘ failed
                         ↘ failed
                                      ↘ failed
```

| 状态 | 含义 |
|------|------|
| `uploaded` | 已上传，待处理 |
| `parsing` | 解析中 |
| `chunking` | 切分中 |
| `chunked` | 切分完成（第三阶段成功终点） |
| `embedding` | 向量化中（后续阶段） |
| `embedded` | 向量化完成（**最终可用状态**，替代历史命名 `indexed`） |
| `failed` | 任一阶段失败 |

迁移说明：

- 新库建表脚本已直接使用含 `embedded` 的枚举。
- 已有库执行 `neon-alter-document-status-embedded.sql`：新增 `embedded`，并将历史 `indexed` 数据更新为 `embedded`。

---

## 4. 交互与前端（决策 A）

- **不启用**前端定时轮询。
- 用户点击「切分」后，状态变为处理中；用户**手动刷新**列表/详情查看进度与结果。
- 后端仍通过 Celery 异步更新状态，无需为轮询单独改接口。

---

## 5. API 风格（决策 C）

维持现有约定：

- URL **不写**动态业务 id 路径段。
- 统一响应：`{ "code": 0, "message": "success", "data": ... }`。

已实现 / 规划路径示例：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/documents/chunk` | body: `{ "id": <doc_id> }`，触发异步切分 |
| GET | `/api/v1/documents/chunks` | query: `document_id`、`page`、`page_size` |
| POST | `/api/v1/documents/embed` | （后续）触发向量化，风格同上 |

---

## 6. 第三阶段边界（不变）

- Phase 3 成功终点仍为 **`chunked`**（切块入库）。
- **不**在本阶段做 Embedding / Milvus 写入。
- 向量化成功后的终态命名统一为 **`embedded`**（决策 B），供后续阶段使用。

---

## 7. 验收要点

- [ ] 多页 PDF：同一页可产生多块；`chunk_index` 全局连续。
- [ ] 空页不产生 chunk。
- [ ] 默认 256/50；改环境变量后 worker 重启生效。
- [ ] 状态流转与前端文案含 `embedded`，不再以 `indexed` 作为产品终态。
- [ ] 前端无轮询；手动刷新可见状态变化。
- [ ] 切分/后续 embed 接口不把 id 放进路径段。
