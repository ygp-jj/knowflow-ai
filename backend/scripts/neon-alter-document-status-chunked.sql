-- =========================================================
-- 文档状态枚举新增 chunked：第 3 阶段成功终态（已切片，待向量化）
-- 第 4 阶段继续：chunked → embedding → indexed
-- =========================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'document_status_enum'
          AND n.nspname = current_schema()
          AND e.enumlabel = 'chunked'
    ) THEN
        ALTER TYPE document_status_enum ADD VALUE 'chunked' BEFORE 'embedding';
    END IF;
END $$;
