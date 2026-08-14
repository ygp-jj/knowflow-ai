-- =========================================================
-- document_chunks 增加父子层级：子块挂 parent_chunk_id
--
-- 约定：
--   章/条等大标题独立成块（父块）；下级分点/正文为子块，写入 parent_chunk_id。
--   检索命中父块后，可按 parent_chunk_id 继续拉取子块。
--
-- 使用：
--   python scripts/create_neon_tables.py --sql-file scripts/neon-alter-document-chunks-parent.sql
-- =========================================================

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS parent_chunk_id INTEGER
    REFERENCES document_chunks(id) ON DELETE SET NULL;

COMMENT ON COLUMN document_chunks.parent_chunk_id IS '父切片 ID；大标题块为 NULL，子块指向所属父标题块';

CREATE INDEX IF NOT EXISTS ix_document_chunks_parent_chunk_id
ON document_chunks (parent_chunk_id);
