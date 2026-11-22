-- Идемпотентное добавление колонки content_hash
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size TEXT;

-- Заполняем hash существующих документов их текущими title (временное решение)
UPDATE documents
SET content_hash = encode(sha256(title::bytea), 'hex'),
    file_size = 'legacy'
WHERE content_hash IS NULL;

-- После заполнения — NOT NULL и UNIQUE
ALTER TABLE documents ALTER COLUMN content_hash SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_content_hash ON documents (content_hash);