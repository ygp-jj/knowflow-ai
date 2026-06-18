# KnowFlow 数据库建表使用说明

这份说明提供两种建表方式，适合不同角色：

- 方法一：前端同学直接在 Neon 控制台执行 SQL
- 方法二：本地开发同学用 Python 脚本一键建表

目标表结构来自《KnowFlow_AI_RAG_智能问答系统_从0到1实现文档》第 9 点，包含：

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

同时会创建：

- 4 个 PostgreSQL 枚举类型
- 外键约束
- 常用查询索引
- `updated_at` 自动更新时间触发器

## 方法一：在 Neon 控制台直接执行 SQL

适合人群：

- 前端开发
- 只想快速把表建出来的人
- 不想跑后端迁移命令的人

操作步骤：

1. 登录 Neon 控制台
2. 进入你的项目数据库
3. 打开 `SQL Editor`
4. 打开本地文件 [neon-create-knowflow-tables.sql](D:/ygp-wx/AIProjects/knowflow-ai/backend/scripts/neon-create-knowflow-tables.sql)
5. 把文件内容全部复制到 SQL Editor
6. 点击 `Run`

执行成功后，你应该能在表列表里看到第 9 点对应的 12 张表。

注意事项：

- 这份 SQL 默认在当前 schema 下建表，Neon 通常是 `public`
- 如果你当前库里已经有同名表，脚本会尽量避免重复创建，但不会帮你自动迁移旧结构
- 建议先确认你连的是正确的 Neon 项目和数据库

## 方法二：本地用 Python 脚本一键建表

适合人群：

- 后端开发
- 本地要重复初始化数据库的人
- 想把 SQL 文件交给脚本自动执行的人

脚本文件：

- [create_neon_tables.py](D:/ygp-wx/AIProjects/knowflow-ai/backend/scripts/create_neon_tables.py)

默认行为：

- 读取 `backend/.env` 里的 `DATABASE_URL`
- 读取 `backend/scripts/neon-create-knowflow-tables.sql`
- 连接目标 PostgreSQL / Neon 数据库
- 执行整份建表 SQL

### 先看执行目标，不真正建表

- 代码在backend文件夹下以虚拟环境激活情况下运行

```powershell
cd D:\ygp-wx\AIProjects\knowflow-ai\backend
python scripts\create_neon_tables.py --dry-run
```

你会看到：

- SQL 文件路径
- 环境文件路径
- 当前读取到的数据库连接串

### 真正执行建表

```powershell
cd D:\ygp-wx\AIProjects\knowflow-ai\backend
python scripts\create_neon_tables.py
```

执行完成后，终端会输出：

```text
KnowFlow 数据库表创建完成。
```

### 可选参数

如果你想换 SQL 文件或环境文件，可以这样传：

```powershell
cd D:\ygp-wx\AIProjects\knowflow-ai\backend
python scripts\create_neon_tables.py --sql-file scripts\neon-create-knowflow-tables.sql --env-file .env
```

## 推荐使用方式

如果你是前端：

1. 用方法一
2. 直接在 Neon 控制台执行 SQL
3. 成功后刷新表列表看结果

如果你是本地开发：

1. 先执行 `--dry-run`
2. 确认数据库连接没问题
3. 再执行正式建表命令

## 我已经验证过的内容

当前仓库里已经通过自动化测试验证：

- SQL 文件可以在 PostgreSQL 临时 schema 中成功执行
- 12 张目标表都能创建成功
- 4 个枚举类型都能创建成功
- Python 脚本的 `--dry-run` 路径可正常运行
