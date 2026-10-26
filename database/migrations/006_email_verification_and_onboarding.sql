-- Migration 006: Email verification, OTP codes, force password change & initial balance guide
-- Personal Expense AI

ALTER TABLE users ADD COLUMN is_verified TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN verification_code VARCHAR(10) NULL;
ALTER TABLE users ADD COLUMN verification_code_expires_at DATETIME NULL;
ALTER TABLE users ADD COLUMN reset_password_code VARCHAR(10) NULL;
ALTER TABLE users ADD COLUMN reset_password_code_expires_at DATETIME NULL;
ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN has_seen_initial_balance_guide TINYINT(1) NOT NULL DEFAULT 0;

