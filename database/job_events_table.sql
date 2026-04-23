CREATE TABLE job_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  job_id CHAR(36) NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  message VARCHAR(255) NULL,
  event_payload_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_job_events_job_id (job_id),
  INDEX idx_job_events_created_at (created_at),
  CONSTRAINT fk_job_events_job
    FOREIGN KEY (job_id) REFERENCES jobs(id)
    ON DELETE CASCADE
);