CREATE TABLE documents (
  id CHAR(36) PRIMARY KEY,
  job_id CHAR(36) NOT NULL,
  document_type VARCHAR(50) NOT NULL,
  storage_path VARCHAR(1024) NOT NULL,
  original_filename VARCHAR(255) NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  size_bytes BIGINT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT fk_documents_job
    FOREIGN KEY (job_id) REFERENCES jobs(id)
    ON DELETE CASCADE,
  INDEX idx_documents_job_id (job_id)
);
