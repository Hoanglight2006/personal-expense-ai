-- MySQL 8 migration: add transaction management columns.
-- Adds payment_method, updated_at, deleted_at, is_deleted to the transactions table.
-- This script is retry-safe (each ALTER is guarded by column existence checks).

DROP PROCEDURE IF EXISTS migrate_transaction_management;
DELIMITER //

CREATE PROCEDURE migrate_transaction_management()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- payment_method ENUM('cash','bank_transfer') NOT NULL DEFAULT 'cash'
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'transactions'
          AND column_name = 'payment_method'
    ) THEN
        ALTER TABLE transactions
            ADD COLUMN payment_method ENUM('cash','bank_transfer') NOT NULL DEFAULT 'cash'
            AFTER transaction_date;
    END IF;

    -- is_deleted BOOLEAN NOT NULL DEFAULT FALSE
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'transactions'
          AND column_name = 'is_deleted'
    ) THEN
        ALTER TABLE transactions
            ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE
            AFTER payment_method;
    END IF;

    -- updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'transactions'
          AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE transactions
            ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP AFTER created_at;
    END IF;

    -- deleted_at DATETIME NULL
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'transactions'
          AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE transactions
            ADD COLUMN deleted_at DATETIME NULL AFTER updated_at;
    END IF;

    -- Index for common queries: active transactions by user and date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE() AND table_name = 'transactions'
          AND index_name = 'ix_txn_user_active_date'
    ) THEN
        ALTER TABLE transactions
            ADD INDEX ix_txn_user_active_date (user_id, is_deleted, transaction_date);
    END IF;

END//

DELIMITER ;
CALL migrate_transaction_management();
DROP PROCEDURE migrate_transaction_management;
