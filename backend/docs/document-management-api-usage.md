# 文档管理接口实现流程与使用说明

## 1. 实现思路

文档管理接口整体复用知识库管理的实现风格，按照 `route -> schema -> service -> model` 分层：

- `backend/app/api/v1/documents.py`
  - 定义 HTTP 接口
  - 处理 query 参数、`multipart/form-data`、统一响应包装
- `backend/app/schemas/document.py`
  - 定义更新请求和文档响应结构
- `backend/app/services/document_service.py`
  - 封装文档上传、分页查询、详情、更新、删除、下载查找等业务逻辑
- `backend/app/services/object_storage.py`
  - 封装 MinIO 的上传、下载、删除操作
- `backend/app/models/document.py`
  - 对应 `documents` 数据表

## 2. 请求链路

### 创建文档

前端上传文件时，调用：

`POST /api/v1/documents/create`

请求进入 `documents.py` 后，后端执行以下流程：

1. 从 `multipart/form-data` 中读取 `knowledge_base_id` 和 `file`
2. 调用 `document_service.create_document()`
3. 在 service 里先检查知识库是否存在
4. 生成 MinIO 对象名，例如：
   - `knowledge-bases/1/20260618103000-uuid.pdf`
5. 调用 `object_storage.upload_file()` 上传到 MinIO
6. 把文档记录写入 `documents` 表
7. 返回统一响应结构给前端

### 下载文档

前端调用：

`GET /api/v1/documents/download?id=1`

后端流程：

1. 按 `id` 查询数据库中的文档记录
2. 读取 `file_path` 对应的 MinIO 对象
3. 通过 `StreamingResponse` 把文件流返回给前端
4. 响应头里带上下载文件名

### 删除文档

前端调用：

`DELETE /api/v1/documents/delete?id=1`

后端流程：

1. 查数据库中的文档记录
2. 根据 `file_path` 删除 MinIO 对象
3. 删除数据库中的文档记录
4. 返回统一成功响应

## 3. 接口列表

- `POST /api/v1/documents/create`
- `GET /api/v1/documents/list?page=1&page_size=10`
- `GET /api/v1/documents/detail?id=1`
- `PUT /api/v1/documents/update`
- `DELETE /api/v1/documents/delete?id=1`
- `GET /api/v1/documents/download?id=1`

所有接口都不把业务 `id` 写在路径里。

## 4. 前端如何调用

### 4.1 创建文档

请求方式：`multipart/form-data`

字段：

- `knowledge_base_id`
- `file`

前端示例：

```javascript
const formData = new FormData();
formData.append("knowledge_base_id", "1");
formData.append("file", file);

const response = await fetch("http://127.0.0.1:8000/api/v1/documents/create", {
  method: "POST",
  body: formData,
});

const result = await response.json();
```
## 9. MinIO 在本地是怎么运行的

`http://127.0.0.1:9001` 是你自己电脑上的本地地址，不是公网地址。

当前项目里，MinIO 是通过 Docker 容器启动的：

```text
你的电脑
  -> Docker Desktop / Docker Engine
    -> MinIO 容器
      -> 9000: MinIO API 端口
      -> 9001: MinIO Web 控制台
```

在 `docker-compose.yml` 里，MinIO 配置了端口映射：

- `9000:9000`
- `9001:9001`

所以：

- `http://127.0.0.1:9001`
  - 本机浏览器访问的 MinIO 控制台
- `localhost:9000`
  - 后端代码访问 MinIO API 的地址

项目里的使用方式是：

1. 前端调用 `POST /api/v1/documents/create` 上传文件。
2. 后端在 `documents.py` 读取 `multipart/form-data`。
3. `document_service.py` 生成对象路径，例如：
   - `knowledge-bases/1/20260618103000-uuid.pdf`
4. `object_storage.py` 把文件上传到 MinIO。
5. PostgreSQL 的 `documents` 表只保存文档记录和 `file_path`。

下载文档时：

1. 前端调用 `GET /api/v1/documents/download?id=1`
2. 后端查数据库拿到 `file_path`
3. 后端从 MinIO 读取对象
4. 后端把文件流返回给前端

删除文档时：

1. 前端调用 `DELETE /api/v1/documents/delete?id=1`
2. 后端先删 MinIO 对象
3. 再删数据库记录

一句话理解：

- PostgreSQL 存“文档记录”
- MinIO 存“文档文件本体”

## 10. 让别人的电脑也访问 `http://127.0.0.1:9001` 怎么做

`127.0.0.1` 只能代表“当前这台电脑自己”，别人电脑不能直接访问你的 `127.0.0.1`。

如果想让同一局域网里的其他电脑访问你这台机器上的 MinIO 控制台，要改成访问你的局域网 IP，例如：

```text
http://192.168.1.23:9001
```

前提条件有 4 个：

1. MinIO 容器已经启动，并且端口映射保持 `9001:9001`
2. 别人的电脑和你的电脑在同一个局域网
3. 你的 Windows 防火墙允许外部访问 `9001` 端口
4. 别人访问的是你的局域网 IP，不是 `127.0.0.1`

查看你本机局域网 IP：

```powershell
ipconfig
```

通常看：

- `IPv4 Address`

例如看到：

```text
IPv4 Address . . . . . . . . . . . : 192.168.1.23
```

那别人就访问：

```text
http://192.168.1.23:9001
```

如果只是让别人访问 MinIO 控制台，这样就够了。

如果还想让别人联调后端文档接口，同样的规则适用：

- Swagger 地址改成 `http://你的局域网IP:8000/docs`
- 后端接口地址改成 `http://你的局域网IP:8000/api/v1/documents/...`

安全注意：

- 当前默认账号密码是 `minioadmin / minioadmin`
- 这种配置只适合本地开发和局域网测试
- 不要直接暴露到公网
- 如果要给团队长期共用，至少要改默认密码，并限制访问范围

### 4.2 分页列表

```javascript
const response = await fetch(
  "http://127.0.0.1:8000/api/v1/documents/list?page=1&page_size=10&knowledge_base_id=1"
);
const result = await response.json();
```

### 4.3 详情

```javascript
const response = await fetch("http://127.0.0.1:8000/api/v1/documents/detail?id=1");
const result = await response.json();
```

### 4.4 修改文件名

```javascript
const response = await fetch("http://127.0.0.1:8000/api/v1/documents/update", {
  method: "PUT",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    id: 1,
    file_name: "renamed.pdf",
  }),
});

const result = await response.json();
```

### 4.5 删除文档

```javascript
const response = await fetch("http://127.0.0.1:8000/api/v1/documents/delete?id=1", {
  method: "DELETE",
});
const result = await response.json();
```

### 4.6 下载文档

如果是浏览器直接下载：

```javascript
window.open("http://127.0.0.1:8000/api/v1/documents/download?id=1", "_blank");
```

如果是前端拿到 `blob` 后自行处理：

```javascript
const response = await fetch("http://127.0.0.1:8000/api/v1/documents/download?id=1");
const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const link = document.createElement("a");
link.href = url;
link.download = "document";
link.click();
window.URL.revokeObjectURL(url);
```

## 5. 统一响应

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败响应示例：

```json
{
  "code": 404,
  "message": "知识库不存在",
  "data": null
}
```

## 6. 本地开发准备

联调文档接口前，先完成这 4 件事：

1. 安装后端新增依赖：

```powershell
cd D:\ygp-wx\AIProjects\knowflow-ai\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. 确认 MinIO 控制台可访问：

- `http://127.0.0.1:9001`
- 用户名：`minioadmin`
- 密码：`minioadmin`

3. 确认 `backend/.env` 中已经配置 MinIO：

- `MINIO_ENDPOINT=localhost:9000`
- `MINIO_ACCESS_KEY=minioadmin`
- `MINIO_SECRET_KEY=minioadmin`
- `MINIO_BUCKET_NAME=knowflow-documents`
- `MINIO_SECURE=false`

4. 启动后端并打开 Swagger：

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

然后访问：

- `http://127.0.0.1:8000/docs`

启动对象存储：

```powershell
docker compose up -d minio
```

MinIO 控制台：

- `http://127.0.0.1:9001`
- 用户名：`minioadmin`
- 密码：`minioadmin`

后端读取的默认 MinIO 配置已与 `docker-compose.yml` 对齐：

- `MINIO_ENDPOINT=localhost:9000`
- `MINIO_ACCESS_KEY=minioadmin`
- `MINIO_SECRET_KEY=minioadmin`
- `MINIO_BUCKET_NAME=knowflow-documents`
- `MINIO_SECURE=false`

## 7. Swagger 使用方式

启动后端后，打开：

`http://127.0.0.1:8000/docs`

在 `Documents` 分组下可以直接测试：

- `create` 会显示文件上传表单
- `list/detail/update/delete` 会显示 query 或 JSON 参数
- `download` 可直接点击触发请求
## 8. Swagger 可直接使用的测试数据

说明：

- 下面这组数据假设数据库里已经存在 `knowledge_base_id=1` 的知识库。
- 如果还没有知识库，先到 `Knowledge Bases` 分组调用 `POST /api/v1/knowledge-bases/create` 创建一个，再把返回的 `id` 用到文档接口里。

### 8.1 创建文档

接口：

- `POST /api/v1/documents/create`

Swagger 填写方式：

- `knowledge_base_id`: `1`
- `file`: 选择一个本地文件，例如：
  - `product-manual.pdf`
  - `api-spec.docx`
  - `faq.txt`

预期结果：

- 返回 `code=0`
- `data.status` 为 `uploaded`
- `data.file_name` 为你上传的文件名

### 8.2 分页列表

接口：

- `GET /api/v1/documents/list`

Swagger 参数：

- `page`: `1`
- `page_size`: `10`
- `knowledge_base_id`: `1`

预期结果：

- 返回当前知识库下的文档列表
- `data.items` 中能看到刚上传的文档

### 8.3 文档详情

接口：

- `GET /api/v1/documents/detail`

Swagger 参数：

- `id`: 使用创建文档接口返回的 `data.id`

示例：

- `id`: `1`

预期结果：

- 返回该文档的 `file_name`、`file_type`、`file_size`、`status`

### 8.4 修改文档文件名

接口：

- `PUT /api/v1/documents/update`

Swagger 请求体：

```json
{
  "id": 1,
  "file_name": "renamed-product-manual.pdf"
}
```

预期结果：

- 返回 `code=0`
- `data.file_name` 更新为 `renamed-product-manual.pdf`

### 8.5 删除文档

接口：

- `DELETE /api/v1/documents/delete`

Swagger 参数：

- `id`: `1`

预期结果：

- 返回 `{ "code": 0, "message": "success", "data": null }`
- 数据库记录删除
- MinIO 对象同步删除

### 8.6 下载文档

接口：

- `GET /api/v1/documents/download`

Swagger 参数：

- `id`: `1`

预期结果：

- 浏览器收到文件流响应
- 响应头里带下载文件名

### 8.7 常见失败测试数据

创建文档时传不存在的知识库：

- `knowledge_base_id`: `999`
- `file`: 任意本地文件

预期结果：

```json
{
  "code": 404,
  "message": "知识库不存在",
  "data": null
}
```

查询不存在的文档：

- `GET /api/v1/documents/detail?id=999`

预期结果：

```json
{
  "code": 404,
  "message": "文档不存在",
  "data": null
}
```
