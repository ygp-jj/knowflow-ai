-- =========================================================
-- 文档状态枚举迁移：新增 embedded，并将历史 indexed 迁移为 embedded
--
-- 终态约定（决策 B）：
--   uploaded → parsing → chunking → chunked → embedding → embedded
--
-- 使用说明：
-- 1. 已有 Neon / 本地库在接入第 4 阶段前执行本脚本。
-- 2. Postgres 无法轻易删除旧枚举值 indexed，可保留但业务代码不再写入。
-- 3. ADD VALUE 与使用新值的 UPDATE 需分步；配合 create_neon_tables.py
--    （autocommit + 按分号拆句）顺序执行即可。
-- =========================================================

-- 步骤 1：枚举增加 embedded（已存在则跳过）
ALTER TYPE document_status_enum
    ADD VALUE IF NOT EXISTS 'embedded';

-- 步骤 2：历史数据 indexed → embedded（无 indexed 行则无影响）
UPDATE documents
SET status = 'embedded'
WHERE status::text = 'indexed';
