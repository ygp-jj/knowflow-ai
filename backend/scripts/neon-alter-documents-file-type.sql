-- =========================================================
-- 扩容 documents.file_type：兼容 Office Open XML 等长 MIME
-- 例如：
--   application/vnd.openxmlformats-officedocument.spreadsheetml.sheet (73)
--   application/vnd.openxmlformats-officedocument.wordprocessingml.document (71)
-- =========================================================

ALTER TABLE documents
    ALTER COLUMN file_type TYPE VARCHAR(255);

COMMENT ON COLUMN documents.file_type IS '文件 MIME 类型，最长 255 字符，兼容 Office Open XML。';
