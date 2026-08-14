-- MySQL 8 migration to support soft-deleting categories.
-- Adds deleted_at column to the categories table.

DROP PROCEDURE IF EXISTS migrate_category_soft_delete;
DELIMITER //

CREATE PROCEDURE migrate_category_soft_delete()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE categories
            ADD COLUMN deleted_at DATETIME NULL AFTER updated_at;
    END IF;

    -- Add index for active categories query (most common)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND index_name = 'ix_category_user_deleted'
    ) THEN
        ALTER TABLE categories
            ADD INDEX ix_category_user_deleted (user_id, deleted_at);
    END IF;
END//

DELIMITER ;
CALL migrate_category_soft_delete();
DROP PROCEDURE migrate_category_soft_delete;
