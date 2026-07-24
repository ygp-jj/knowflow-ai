-- =========================================================
-- 文档状态枚举新增 chunked：第 3 阶段成功终态（已切片，待向量化）
-- 第 4 阶段继续：chunked → embedding → embedded
--
-- 已有 Neon / 本地库请执行本脚本后再跑 Celery 切片任务。
-- 注意：不要包在 BEGIN/COMMIT 或 DO $$ 里执行 ADD VALUE。
-- =========================================================

ALTER TYPE document_status_enum
    ADD VALUE IF NOT EXISTS 'chunked' BEFORE 'embedding';
