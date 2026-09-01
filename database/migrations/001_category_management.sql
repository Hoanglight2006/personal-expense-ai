-- MySQL 8 migration for personal category management.
-- This script is retry-safe after interrupted DDL. Category merges are irreversible;
-- take a database backup before applying it in production.

DROP PROCEDURE IF EXISTS migrate_category_management;
DELIMITER //

CREATE PROCEDURE migrate_category_management()
BEGIN
    DECLARE old_fk VARCHAR(64);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- Do not start an upgrade when existing rows already violate ownership.
    IF EXISTS (
        SELECT 1
        FROM transactions AS t
        JOIN categories AS c ON c.id = t.category_id
        WHERE t.user_id <> c.user_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migration aborted: transaction/category ownership mismatch';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM budgets AS b
        JOIN categories AS c ON c.id = b.category_id
        WHERE b.user_id <> c.user_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migration aborted: budget/category ownership mismatch';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND column_name = 'name_normalized'
    ) THEN
        ALTER TABLE categories ADD COLUMN name_normalized VARCHAR(150) NULL AFTER name;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND column_name = 'icon'
    ) THEN
        ALTER TABLE categories
            ADD COLUMN icon VARCHAR(30) NOT NULL DEFAULT 'other' AFTER name_normalized;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND column_name = 'color'
    ) THEN
        ALTER TABLE categories
            ADD COLUMN color CHAR(7) NOT NULL DEFAULT '#D69A23' AFTER icon;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND column_name = 'is_active'
    ) THEN
        ALTER TABLE categories
            ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER color;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE categories
            ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP AFTER created_at;
    END IF;

    START TRANSACTION;

    -- MySQL cannot reproduce Python NFKC/casefold, but LOWER(TRIM()) preserves
    -- legacy behavior. All new writes use the application normalization key.
    UPDATE categories
    SET name = TRIM(name), name_normalized = LOWER(TRIM(name));

    DROP TEMPORARY TABLE IF EXISTS tmp_category_merge;
    CREATE TEMPORARY TABLE tmp_category_merge (
        drop_id INT PRIMARY KEY,
        keep_id INT NOT NULL
    );
    INSERT INTO tmp_category_merge (drop_id, keep_id)
    SELECT c.id, duplicates.keep_id
    FROM categories AS c
    JOIN (
        SELECT user_id, name_normalized, MIN(id) AS keep_id
        FROM categories
        GROUP BY user_id, name_normalized
        HAVING COUNT(*) > 1
    ) AS duplicates
      ON duplicates.user_id = c.user_id
     AND duplicates.name_normalized = c.name_normalized
    WHERE c.id <> duplicates.keep_id;

    -- Roll budgets up before category IDs are changed, otherwise the existing
    -- unique (user, category, month, year) constraint can reject the update.
    DROP TEMPORARY TABLE IF EXISTS tmp_budget_merge;
    CREATE TEMPORARY TABLE tmp_budget_merge AS
    SELECT
        b.id AS budget_id,
        COALESCE(m.keep_id, b.category_id) AS target_category_id,
        MIN(b.id) OVER (
            PARTITION BY b.user_id, COALESCE(m.keep_id, b.category_id), b.month, b.year
        ) AS keep_budget_id,
        SUM(b.amount) OVER (
            PARTITION BY b.user_id, COALESCE(m.keep_id, b.category_id), b.month, b.year
        ) AS total_amount
    FROM budgets AS b
    LEFT JOIN tmp_category_merge AS m ON m.drop_id = b.category_id;

    DELETE b
    FROM budgets AS b
    JOIN tmp_budget_merge AS rollup ON rollup.budget_id = b.id
    WHERE rollup.budget_id <> rollup.keep_budget_id;

    UPDATE budgets AS b
    JOIN tmp_budget_merge AS rollup
      ON rollup.budget_id = b.id AND rollup.keep_budget_id = b.id
    SET b.category_id = rollup.target_category_id,
        b.amount = rollup.total_amount;

    UPDATE transactions AS t
    JOIN tmp_category_merge AS m ON m.drop_id = t.category_id
    SET t.category_id = m.keep_id;

    DELETE c
    FROM categories AS c
    JOIN tmp_category_merge AS m ON m.drop_id = c.id;

    COMMIT;

    ALTER TABLE categories MODIFY COLUMN name_normalized VARCHAR(150) NOT NULL;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND index_name = 'uq_category_user_normalized_name'
    ) THEN
        ALTER TABLE categories
            ADD CONSTRAINT uq_category_user_normalized_name
            UNIQUE (user_id, name_normalized);
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND index_name = 'uq_category_user_name_type'
    ) THEN
        ALTER TABLE categories DROP INDEX uq_category_user_name_type;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND column_name = 'type'
    ) THEN
        ALTER TABLE categories DROP COLUMN type;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE() AND table_name = 'categories'
          AND index_name = 'uq_category_id_user'
    ) THEN
        ALTER TABLE categories
            ADD CONSTRAINT uq_category_id_user UNIQUE (id, user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_schema = DATABASE() AND table_name = 'transactions'
          AND constraint_name = 'fk_transaction_category_owner'
    ) THEN
        SET old_fk = (
            SELECT MIN(kcu.constraint_name)
            FROM information_schema.key_column_usage AS kcu
            WHERE kcu.constraint_schema = DATABASE()
              AND kcu.table_name = 'transactions'
              AND kcu.column_name = 'category_id'
              AND kcu.referenced_table_name = 'categories'
        );
        IF old_fk IS NOT NULL THEN
            SET @ddl = CONCAT('ALTER TABLE transactions DROP FOREIGN KEY `', old_fk, '`');
            PREPARE statement FROM @ddl;
            EXECUTE statement;
            DEALLOCATE PREPARE statement;
        END IF;
        ALTER TABLE transactions
            ADD CONSTRAINT fk_transaction_category_owner
            FOREIGN KEY (category_id, user_id)
            REFERENCES categories (id, user_id) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_schema = DATABASE() AND table_name = 'budgets'
          AND constraint_name = 'fk_budget_category_owner'
    ) THEN
        SET old_fk = (
            SELECT MIN(kcu.constraint_name)
            FROM information_schema.key_column_usage AS kcu
            WHERE kcu.constraint_schema = DATABASE()
              AND kcu.table_name = 'budgets'
              AND kcu.column_name = 'category_id'
              AND kcu.referenced_table_name = 'categories'
        );
        IF old_fk IS NOT NULL THEN
            SET @ddl = CONCAT('ALTER TABLE budgets DROP FOREIGN KEY `', old_fk, '`');
            PREPARE statement FROM @ddl;
            EXECUTE statement;
            DEALLOCATE PREPARE statement;
        END IF;
        ALTER TABLE budgets
            ADD CONSTRAINT fk_budget_category_owner
            FOREIGN KEY (category_id, user_id)
            REFERENCES categories (id, user_id) ON DELETE CASCADE;
    END IF;

    DROP TEMPORARY TABLE IF EXISTS tmp_budget_merge;
    DROP TEMPORARY TABLE IF EXISTS tmp_category_merge;
END//

DELIMITER ;
CALL migrate_category_management();
DROP PROCEDURE migrate_category_management;
