-- =========================================================
-- 文档状态枚举：新增 embedded，并将历史 indexed 迁移为 embedded
-- 终态约定：chunked → embedding → embedded
--
-- 说明：
-- 1. Postgres 无法轻易删除旧枚举值 indexed，可保留但业务不再写入。
-- 2. ADD VALUE 与使用新值的 UPDATE 需分步；本脚本在 autocommit 下顺序执行。
-- =========================================================

ALTER TYPE document_status_enum
    ADD VALUE IF NOT EXISTS 'embedded';

-- 历史数据：indexed → embedded（若无 indexed 行则无影响）
UPDATE documents
SET status = 'embedded'
WHERE status::text = 'indexed';
