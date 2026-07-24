## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11+) |
| 关系数据库 | PostgreSQL 16 |
| 向量数据库 | Milvus 2.5 |
| 缓存 / 消息队列 | Redis 7 + Celery |
| 对象存储 | MinIO |
| 配置中心 | etcd |
| LLM | DeepSeek / OpenAI 兼容接口 |
| 依赖管理 | pip + requirements.txt |

数据库，使用了线上的 Neon.tech

---

## 环境要求

- Python 3.11+
- Docker & Docker Compose
- Git

## 编码规范

### 代码注释：使用/**  */,新增的方法、参数、变量需要备注

### Git / PR 备注语言
- `git commit` 提交说明、PR 标题与正文、PR 评论、以及需要人工阅读的备注说明，**一律使用中文**。
- 代码标识符（变量名、函数名、分支名前缀等）仍按既有英文/约定风格，不要求改成中文。

### 前端Vue 组件编写
- 必须使用 **`<script setup>`** 语法糖，不再使用 `export default`。
- 所有 `.vue` 文件的 `<script>` 标签 **不要加 `lang="ts"`**，直接写 JavaScript。
- 使用 `ref`、`reactive`、`computed`、`watch` 等 API 时，从 `vue` 导入，不需要类型注解。
- 组件名使用 **PascalCase** (大驼峰)，模板中也用 PascalCase 引用组件。

**正确示例:**
```vue
<template>
  <div>
    <a-button @click="handleClick">点击</a-button>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { AButton } from 'ant-design-vue';

const count = ref(0);

function handleClick() {
  count.value++;
}
</script>

<style scoped>
</style>
```

## 后端知识库管理接口约定

- 第一版知识库管理的 `owner_id` 由前端显式传入，便于联调测试，并为后续登录态接入预留扩展空间。
- 知识库管理第一版只实现基础 CRUD：创建、分页列表、详情、修改、删除。
- 知识库接口不要把业务 `id` 写在 URL 路径段里，详情和删除用查询参数传入 `id`，修改用请求体传入 `id`。
- 知识库接口路径固定为：
  - `POST /api/v1/knowledge-bases/create`
  - `GET /api/v1/knowledge-bases/list?owner_id=<owner_id>&page=1&page_size=10`
  - `GET /api/v1/knowledge-bases/detail?id=1&owner_id=<owner_id>`
  - `PUT /api/v1/knowledge-bases/update`
  - `DELETE /api/v1/knowledge-bases/delete?id=1&owner_id=<owner_id>`
- 知识库接口统一响应格式为 `{ "code": 0, "message": "success", "data": ... }`，错误时 `data` 返回 `null`。
- 知识库列表必须分页，返回 `items`、`total`、`page`、`page_size`。
- 删除知识库前必须检查是否存在关联文档；如果存在文档，接口返回错误，不执行删除。

## 后端文档管理接口约定

- 第一版文档管理采用与知识库管理一致的接口风格，URL 中不要写动态参数。
- 文档创建接口使用 `multipart/form-data`，前端通过 `knowledge_base_id` 和 `file` 上传文档。
- 文档管理接口路径固定为：
  - `POST /api/v1/documents/create`
  - `GET /api/v1/documents/list?page=1&page_size=10`
  - `GET /api/v1/documents/detail?id=1`
  - `PUT /api/v1/documents/update`
  - `DELETE /api/v1/documents/delete?id=1`
  - `GET /api/v1/documents/download?id=1`
  - `GET /api/v1/documents/chunks?document_id=1&page=1&page_size=10`
- 文档列表支持可选 `knowledge_base_id` 过滤，并返回分页结构 `items`、`total`、`page`、`page_size`。
- 文档统一响应格式为 `{ "code": 0, "message": "success", "data": ... }`，错误时 `data` 返回 `null`。
- 文档文件在开发阶段直接存入本地 Docker 启动的 MinIO。
- 删除文档时必须同时删除数据库记录和 MinIO 对象。
- 下载文档时通过后端下载接口返回文件流，不直接暴露 MinIO 真实对象地址。

## 后端文档解析与切片约定（第 3 阶段 / 方案 A）

- 上传成功后由 Celery 异步解析与切片，HTTP 接口立即返回，不等待处理完成。
- 本阶段成功终态为 `chunked`（已切片，待向量化）；**不要**在本阶段写入 Milvus，也**不要**将成功状态标为 `indexed`。
- 文档状态流转：`uploaded → parsing → chunking → chunked`；失败为 `failed` 并写入 `error_message`。
- `embedding` / `indexed` 留给第 4 阶段：`chunked → embedding → indexed`。
- 切片结果写入 `document_chunks`，并更新 `documents.chunk_count`；`vector_id` 本阶段保持为空。
- MVP 切片参数：`chunk_size=800`，`chunk_overlap=120`（字符）。
- 本阶段支持解析：PDF / DOCX / TXT / Markdown；不支持类型任务失败。
- 推荐补充接口：`GET /api/v1/documents/chunks?document_id=<id>&page=1&page_size=10`。
- 详细设计与任务拆分见：
  - `docs/phase3-document-parse-chunk-design.md`
  - `docs/phase3-document-parse-chunk-plan.md`
  - `docs/phase3-document-parse-chunk-usage.md`
