CREATE TABLE jobs (
  id CHAR(36) PRIMARY KEY,
  exchange VARCHAR(20) NOT NULL,
  tax_year INT NOT NULL,
  account_holder VARCHAR(255) NOT NULL COMMENT 'Email in Hanko',
  uid VARCHAR(128) NOT NULL COMMENT 'User Id in Hanko',
  status VARCHAR(20) NOT NULL,
  request_payload_json JSON NOT NULL,
  result_payload_json JSON NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  INDEX idx_jobs_status (status),
  INDEX idx_jobs_created_at (created_at)
);
