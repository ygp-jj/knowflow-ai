# KnowFlow 演示数据使用说明

这份说明用于给已经建好的 KnowFlow 数据库写入一套“公司制度知识库”主题的演示数据。

这套数据的特点：

- 每张表严格 4 条数据
- 数据不是随机占位，而是彼此有关联
- 适合前端页面直接演示
- 适合知识库、文档、聊天、引用来源、反馈、评测页面联动展示
- **演示登录账号**：用户名见 `users` 表（默认联调 `hr_admin`），密码统一 `demo123456`（bcrypt）

本次会写入的表包括：

- `users`
- `knowledge_bases`
- `documents`
- `document_chunks`
- `chat_sessions`
- `chat_messages`
- `chat_references`
- `prompt_templates`
- `model_configs`
- `question_feedbacks`
- `evaluation_cases`
- `evaluation_runs`

## 数据主题说明

整套演示数据围绕 4 个制度主题展开：

1. 员工请假制度
2. 员工报销制度
3. 新员工入职制度
4. 远程办公制度

对应的前端演示效果包括：

- 4 个知识库
- 4 份制度文档
- 4 条文档切片摘要
- 4 个聊天会话
- 4 条助手回答
- 4 条引用来源
- 4 条用户反馈
- 4 条评测题
- 4 条评测结果

## 方法一：在 Neon 控制台直接执行 seed SQL

适合人群：

- 前端开发
- 只想快速把演示数据灌进去的人
- 不想跑本地脚本的人

操作步骤：

1. 登录 Neon 控制台
2. 打开目标数据库
3. 进入 `SQL Editor`
4. 打开本地文件 [neon-seed-knowflow-data.sql](D:/ygp-wx/AIProjects/knowflow-ai/backend/scripts/neon-seed-knowflow-data.sql)
5. 把全部 SQL 内容复制到 SQL Editor
6. 点击 `Run`

执行完成后，你的所有业务表都应该有 4 条演示数据。

注意事项：

- 这份脚本默认表已经创建好
- 这份脚本使用固定 ID 建立跨表关联
- 再次执行时会按主键更新，不会重复插入同一批数据
- **登录鉴权**：4 个用户密码统一为 `demo123456`（bcrypt）。若库中已是旧明文/占位哈希，重跑本 seed 或执行：
  `UPDATE users SET hashed_password = '$2b$12$jLRQnn2kAn3atfpId52Xsuxk58qSlsblfVt4mDxlwZEFHTyNbYP..';`

## 方法二：本地 Python 脚本一键写入演示数据

适合人群：

- 后端开发
- 需要重复初始化数据库演示环境的人
- 想把 SQL 文件交给脚本统一执行的人

脚本文件：

- [seed_neon_data.py](D:/ygp-wx/AIProjects/knowflow-ai/backend/scripts/seed_neon_data.py)

默认行为：

- 读取 `backend/.env` 里的 `DATABASE_URL`
- 读取 `backend/scripts/neon-seed-knowflow-data.sql`
- 连接目标 PostgreSQL / Neon 数据库
- 执行整份 seed SQL

### 先看执行目标，不真正写入数据

```powershell
cd D:\ygp-wx\AIProjects\knowflow-ai\backend
python scripts\seed_neon_data.py --dry-run
```

你会看到：

- Seed SQL 文件路径
- 环境文件路径
- 当前数据库连接串

### 真正执行写入

```powershell
cd D:\ygp-wx\AIProjects\knowflow-ai\backend
python scripts\seed_neon_data.py
```

执行成功后，终端会输出：

```text
KnowFlow 演示数据写入完成。
```

### 自定义参数

如果你想换 SQL 文件或环境文件，可以这样传：

```powershell
cd D:\ygp-wx\AIProjects\knowflow-ai\backend
python scripts\seed_neon_data.py --sql-file scripts\neon-seed-knowflow-data.sql --env-file .env
```

## 推荐操作顺序

如果数据库还是空的，推荐顺序是：

1. 先执行建表脚本
2. 再执行演示数据脚本

如果你已经建好表，现在只需要执行：

1. `python scripts\seed_neon_data.py --dry-run`
2. `python scripts\seed_neon_data.py`

## 我已经验证过的内容

当前仓库里已经通过自动化测试验证：

- seed SQL 能在 PostgreSQL 临时 schema 中成功执行
- 每张表都能写入且恰好 4 条数据
- 反馈表引用的消息都是 `assistant`
- Python 脚本的 `--dry-run` 路径可正常运行
