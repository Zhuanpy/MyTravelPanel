-- Add email reminder fields to todos table
ALTER TABLE todos
  ADD COLUMN IF NOT EXISTS recipient_email VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS send_email TINYINT(1) NOT NULL DEFAULT 0;


