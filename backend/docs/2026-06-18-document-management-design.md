# 文档管理设计

## 目标

实现与知识库管理风格一致的文档管理接口，支持真实文件上传到本地 Docker 启动的 MinIO，支持文档分页列表、详情、修改、删除和下载，接口路径中不使用动态参数。

## 第一版范围

- 使用 `multipart/form-data` 上传文件。
- 文件存入本地 Docker 启动的 MinIO。
- 创建文档时校验 `knowledge_base_id` 对应知识库存在。
- 提供分页列表，并支持按 `knowledge_base_id` 筛选。
- 提供详情、修改、删除、下载接口。
- 删除文档时同时删除数据库记录和 MinIO 对象。
- 下载通过后端接口读取 MinIO 后返回文件流，不直接暴露对象地址。
- 统一响应格式沿用 `{ "code": 0, "message": "success", "data": ... }`。

## 接口设计

- `POST /api/v1/documents/create`
- `GET /api/v1/documents/list?page=1&page_size=10`
- `GET /api/v1/documents/detail?id=1`
- `PUT /api/v1/documents/update`
- `DELETE /api/v1/documents/delete?id=1`
- `GET /api/v1/documents/download?id=1`

### 创建接口

- 请求类型：`multipart/form-data`
- 表单字段：
  - `knowledge_base_id`
  - `file`
- 后端行为：
  - 校验知识库存在。
  - 将文件写入 MinIO。
  - 将 `file_name`、`file_type`、`file_path`、`file_size`、`status`、`chunk_count` 落库。
  - 默认 `status="uploaded"`，`chunk_count=0`。

### 列表接口

- 支持 `page`、`page_size`
- 支持可选 `knowledge_base_id`
- 返回 `items`、`total`、`page`、`page_size`

### 修改接口

- 第一版只允许修改 `file_name`
- 请求体通过 JSON 传入 `id` 和 `file_name`

### 删除接口

- 查询参数传入 `id`
- 后端先查文档，再删除 MinIO 对象，最后删除数据库记录

### 下载接口

- 查询参数传入 `id`
- 后端从 MinIO 读取对象，并将文件流返回给前端

## 技术方案

- 在 `backend/app/core/config.py` 中补充 MinIO 配置。
- 新增对象存储服务模块，封装上传、下载、删除。
- 为避免测试依赖真实 MinIO，存储服务通过依赖注入或可替换工厂提供。
- 测试使用 SQLite 内存库和内存对象存储假实现，验证接口行为与约定。

## 前端使用说明范围

实现完成后，需要同时提供：

- 每个接口的 URL、方法、参数说明
- `multipart/form-data` 上传示例
- 下载接口调用方式
- Swagger 中的使用方式
- 成功和失败返回示例
