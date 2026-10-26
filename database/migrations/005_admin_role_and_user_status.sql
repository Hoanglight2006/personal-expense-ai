-- MySQL 8 migration to support Admin role and account lock status.
-- Adds role and is_locked columns, plus index to the users table.

DROP PROCEDURE IF EXISTS migrate_admin_role_and_status;
DELIMITER //

CREATE PROCEDURE migrate_admin_role_and_status()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'users'
          AND column_name = 'role'
    ) THEN
        ALTER TABLE users
            ADD COLUMN role ENUM('user', 'admin') NOT NULL DEFAULT 'user' AFTER avatar_url;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'users'
          AND column_name = 'is_locked'
    ) THEN
        ALTER TABLE users
            ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT FALSE AFTER role;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE() AND table_name = 'users'
          AND index_name = 'idx_users_role_status'
    ) THEN
        ALTER TABLE users
            ADD INDEX idx_users_role_status (role, is_locked);
    END IF;
END//

DELIMITER ;
CALL migrate_admin_role_and_status();
DROP PROCEDURE migrate_admin_role_and_status;

