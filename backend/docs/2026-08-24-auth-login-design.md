# 设计：登录鉴权（JWT）

> 日期：2026-08-24  
> 状态：已确认，待实现  
> 前置：5B 多轮会话已落地  
> 姐妹文档：`backend/docs/2026-08-24-chat-acceptance-references-design.md`（先实现）

## 1. 目标

| 目标 | 不做 |
|------|------|
| 用户名密码登录，签发 JWT | 注册接口 |
| 业务 API 需登录；身份以 Token 为准 | 第三方 OAuth |
| 前端登录页 + 路由守卫 + 401 跳转 | 刷新 Token / 双 Token |

## 2. 登录方式

- **凭证**：`username` + `password`
- **种子用户**：更新 Neon seed，将 `hashed_password` 改为 **bcrypt** 哈希
- **演示密码**：统一 `demo123456`（写入 `neon-seed-knowflow-data-usage.md` 等说明，勿提交真实生产密码）
- **默认联调账号**：`hr_admin`（id=101），与现有 `VITE_DEFAULT_OWNER_ID` 数据对齐

## 3. Token 约定

| 项 | 结论 |
|----|------|
| 存储 | 前端 `localStorage` |
| 有效期 | 默认 **7 天**（`JWT_EXPIRE_MINUTES`，可 env 覆盖） |
| 请求头 | `Authorization: Bearer <access_token>` |
| 登出 | 前端清除 token + user 缓存 |

## 4. 后端接口

### 4.1 公开（无需 Token）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | body: `{ username, password }` → `{ access_token, token_type, user }` |
| GET | `/health` | 健康检查 |

### 4.2 需登录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/auth/me` | 当前用户信息 |

### 4.3 业务接口（全部需 Bearer）

- 知识库：`/api/v1/knowledge-bases/*`
- 文档：`/api/v1/documents/*`
- 聊天：`/api/v1/chat/*`（含无会话 `/ask`、`/ask-stream` 与会话 CRUD、`sessions/ask-stream`）

**身份规则：**

- `owner_id` / `user_id` **不再由前端传入**
- 服务端从 JWT 解析 `sub` → 当前用户 `id`，用于知识库归属、会话归属、列表过滤等

## 5. 后端实现要点

### 5.1 依赖

- `python-jose[cryptography]`：JWT
- `passlib[bcrypt]`：密码哈希

### 5.2 配置（`config.py` / `.env`）

- `JWT_SECRET_KEY`（生产必须改）
- `JWT_ALGORITHM=HS256`
- `JWT_EXPIRE_MINUTES=10080`（7 天）

### 5.3 模块划分

| 模块 | 职责 |
|------|------|
| `app/core/security.py` | hash / verify、`create_access_token`、`decode_access_token` |
| `app/core/deps.py` | `get_current_user`（HTTPBearer） |
| `app/schemas/auth.py` | `LoginRequest`、`LoginRead`、`UserRead` |
| `app/services/auth_service.py` | 校验用户、签发 Token |
| `app/api/v1/auth.py` | `/login`、`/me` |

### 5.4 Schema / 路由改造

- `KnowledgeBaseCreate/Update`：移除 `owner_id` 字段
- `ChatSessionCreate/Update/AskStream`：移除 `user_id` 字段
- 各业务 router 增加 `current_user: User = Depends(get_current_user)`
- 服务层 `create_knowledge_base(..., owner_id=current_user.id)` 等由路由注入

### 5.5 种子数据

- 更新 `backend/scripts/neon-seed-knowflow-data.sql` 中 4 个用户的 `hashed_password` 为 `demo123456` 的 bcrypt
- 已有库需执行一次性 UPDATE 或重跑 seed（文档说明）

## 6. 前端实现要点

### 6.1 页面与路由

- 新增 `LoginPage.vue`，路径 `/login`
- 管理台路由（`AdminLayout` 下）加 **beforeEach**：无 token → 重定向 `/login`
- 已登录访问 `/login` → 重定向首页（如 `/knowledge-bases`）

### 6.2 状态与 HTTP

- `stores/auth.js` 或 composable：`token`、`user`；`login` / `logout` / `loadMe`
- `http.js`：请求拦截器附加 `Authorization`；响应 401 → 清 token 并 `router.push('/login')`
- `chat-service.js` 流式 `fetch`：同样带 Bearer

### 6.3 替换硬编码

- 移除各页面对 `DEFAULT_OWNER_ID` 的业务传参
- 顶栏展示 `username`，提供「退出登录」
- 保留 `constants/app.js` 时可仅作迁移过渡，不再用于 API

## 7. 错误与响应

- 登录失败：`{ code: 401, message: "用户名或密码错误", data: null }`
- Token 无效/过期：HTTP 401，前端统一跳转登录
- 与现有 `{ code, message, data }` 风格一致

## 8. 验收

- [ ] `hr_admin` / `demo123456` 可登录并拿到 token
- [ ] 无 token 访问 `/knowledge-bases/list` 返回 401
- [ ] 带 token 可正常 CRUD 知识库、文档、会话
- [ ] 前端未登录打开 `/chat` 跳转 `/login`
- [ ] 登出后 token 清除，再访问业务页需重新登录
- [ ] Token 过期或伪造 token → 401 并跳转登录
- [ ] 单测：`test_auth_api.py` 登录成功/失败、/me 需 Bearer

## 9. 非目标

- 注册、找回密码、验证码
- Refresh Token
- RBAC / 多角色权限（本期仅「登录用户只能操作自己的数据」）
- Celery Worker 内 JWT（Worker 仍用服务账号/配置，不经过 HTTP）

## 10. 决策记录

| 项 | 结论 |
|----|------|
| 登录 | 用户名 + 密码 + JWT |
| 种子密码 | 统一 `demo123456`（bcrypt） |
| Token 存储 | localStorage，7 天 |
| 身份 | JWT 为准，前端不传 owner_id/user_id |
| 保护范围 | 全部业务 API + 无会话 ask |
| 401 行为 | 清 token + 跳登录页 |

## 11. 实施顺序

1. 完成 **文档一**（验收 + 引用折叠）  
2. 后端 auth + 改造业务路由/Schema  
3. 更新 seed + 单测  
4. 前端 Login + 守卫 + 去硬编码  
5. 更新 `AGENTS.md` 约定  
