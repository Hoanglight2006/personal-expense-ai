-- Add an auditable, idempotent withdrawal ledger for Saving Goals.
-- MySQL 8; safe to retry because the table is created only when missing.

CREATE TABLE IF NOT EXISTS saving_withdrawals (
    id INT NOT NULL AUTO_INCREMENT,
    saving_goal_id INT NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    note VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT ck_saving_withdrawal_amount_positive CHECK (amount > 0),
    CONSTRAINT fk_saving_withdrawal_goal
        FOREIGN KEY (saving_goal_id)
        REFERENCES saving_goals (id)
        ON DELETE CASCADE,
    CONSTRAINT uq_saving_withdrawal_goal_key
        UNIQUE (saving_goal_id, idempotency_key),
    INDEX ix_saving_withdrawals_saving_goal_id (saving_goal_id)
) ENGINE=InnoDB;

-- Record which rows truly came from the draft schema before assigning fallback
-- keys. The marker survives a failed migration so a retry can resume, but is
-- dropped after a successful backfill. Public idempotency-key content is never
-- used to classify a withdrawal as legacy.
CREATE TABLE IF NOT EXISTS migration_004_legacy_withdrawals (
    withdrawal_id INT NOT NULL,
    PRIMARY KEY (withdrawal_id),
    CONSTRAINT fk_migration_004_legacy_withdrawal
        FOREIGN KEY (withdrawal_id)
        REFERENCES saving_withdrawals (id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- Upgrade databases that already created an earlier draft of this table before
-- idempotency_key was introduced. Existing rows receive a deterministic key.
DROP PROCEDURE IF EXISTS migrate_saving_withdrawal_idempotency;

DELIMITER //
CREATE PROCEDURE migrate_saving_withdrawal_idempotency()
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'saving_withdrawals'
          AND COLUMN_NAME = 'idempotency_key'
    ) THEN
        ALTER TABLE saving_withdrawals
            ADD COLUMN idempotency_key VARCHAR(64) NULL AFTER amount;
    END IF;

    INSERT IGNORE INTO migration_004_legacy_withdrawals (withdrawal_id)
    SELECT id
    FROM saving_withdrawals
    WHERE idempotency_key IS NULL OR idempotency_key = '';

    UPDATE saving_withdrawals
    SET idempotency_key = CONCAT('legacy-', id)
    WHERE idempotency_key IS NULL OR idempotency_key = '';

    ALTER TABLE saving_withdrawals
        MODIFY COLUMN idempotency_key VARCHAR(64) NOT NULL;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'saving_withdrawals'
          AND INDEX_NAME = 'uq_saving_withdrawal_goal_key'
    ) THEN
        ALTER TABLE saving_withdrawals
            ADD CONSTRAINT uq_saving_withdrawal_goal_key
            UNIQUE (saving_goal_id, idempotency_key);
    END IF;
END//
DELIMITER ;

CALL migrate_saving_withdrawal_idempotency();
DROP PROCEDURE IF EXISTS migrate_saving_withdrawal_idempotency;

CREATE TABLE IF NOT EXISTS saving_withdrawal_allocations (
    id INT NOT NULL AUTO_INCREMENT,
    withdrawal_id INT NOT NULL,
    contribution_id INT NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_saving_withdrawal_allocation_amount_positive CHECK (amount > 0),
    CONSTRAINT uq_withdrawal_contribution
        UNIQUE (withdrawal_id, contribution_id),
    CONSTRAINT fk_withdrawal_allocation_withdrawal
        FOREIGN KEY (withdrawal_id)
        REFERENCES saving_withdrawals (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_withdrawal_allocation_contribution
        FOREIGN KEY (contribution_id)
        REFERENCES saving_contributions (id)
        ON DELETE CASCADE,
    INDEX ix_withdrawal_allocations_withdrawal_id (withdrawal_id),
    INDEX ix_withdrawal_allocations_contribution_id (contribution_id)
) ENGINE=InnoDB;

-- Backfill withdrawals created by the draft implementation. FIFO cumulative
-- intervals deterministically map each withdrawal to the contributions it
-- consumed. Preflights stop the migration if the old ledger cannot be inferred
-- without violating withdrawal totals, contribution capacity, or current_amount.
DROP PROCEDURE IF EXISTS backfill_legacy_withdrawal_allocations;

DELIMITER //
CREATE PROCEDURE backfill_legacy_withdrawal_allocations()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        DROP TEMPORARY TABLE IF EXISTS tmp_withdrawal_allocation_candidate;
        RESIGNAL;
    END;

    DROP TEMPORARY TABLE IF EXISTS tmp_withdrawal_allocation_candidate;
    CREATE TEMPORARY TABLE tmp_withdrawal_allocation_candidate (
        withdrawal_id INT NOT NULL,
        contribution_id INT NOT NULL,
        amount NUMERIC(15, 2) NOT NULL,
        PRIMARY KEY (withdrawal_id, contribution_id),
        INDEX ix_tmp_withdrawal_candidate_contribution_id (contribution_id)
    ) ENGINE=InnoDB;

    START TRANSACTION;

    -- Preserve allocations created by the final implementation. The temporary
    -- table represents the complete post-migration ledger used by preflight.
    INSERT INTO tmp_withdrawal_allocation_candidate (
        withdrawal_id,
        contribution_id,
        amount
    )
    SELECT
        allocation.withdrawal_id,
        allocation.contribution_id,
        allocation.amount
    FROM saving_withdrawal_allocations AS allocation
    INNER JOIN saving_withdrawals AS withdrawal
        ON withdrawal.id = allocation.withdrawal_id
    LEFT JOIN migration_004_legacy_withdrawals AS legacy
        ON legacy.withdrawal_id = withdrawal.id
    WHERE legacy.withdrawal_id IS NULL;

    -- Infer only draft withdrawals. Nothing is written to the real allocation
    -- table until every preflight below has passed.
    INSERT INTO tmp_withdrawal_allocation_candidate (
        withdrawal_id,
        contribution_id,
        amount
    )
    SELECT
        withdrawal_intervals.withdrawal_id,
        contribution_intervals.contribution_id,
        LEAST(
            withdrawal_intervals.interval_end,
            contribution_intervals.interval_end
        ) - GREATEST(
            withdrawal_intervals.interval_start,
            contribution_intervals.interval_start
        ) AS allocated_amount
    FROM (
        SELECT
            withdrawal.id AS withdrawal_id,
            withdrawal.saving_goal_id,
            SUM(withdrawal.amount) OVER (
                PARTITION BY withdrawal.saving_goal_id
                ORDER BY withdrawal.created_at, withdrawal.id
                ROWS UNBOUNDED PRECEDING
            ) - withdrawal.amount AS interval_start,
            SUM(withdrawal.amount) OVER (
                PARTITION BY withdrawal.saving_goal_id
                ORDER BY withdrawal.created_at, withdrawal.id
                ROWS UNBOUNDED PRECEDING
            ) AS interval_end
        FROM saving_withdrawals AS withdrawal
        INNER JOIN migration_004_legacy_withdrawals AS legacy
            ON legacy.withdrawal_id = withdrawal.id
    ) AS withdrawal_intervals
    INNER JOIN (
        SELECT
            contribution.id AS contribution_id,
            contribution.saving_goal_id,
            SUM(contribution.amount) OVER (
                PARTITION BY contribution.saving_goal_id
                ORDER BY contribution.created_at, contribution.id
                ROWS UNBOUNDED PRECEDING
            ) - contribution.amount AS interval_start,
            SUM(contribution.amount) OVER (
                PARTITION BY contribution.saving_goal_id
                ORDER BY contribution.created_at, contribution.id
                ROWS UNBOUNDED PRECEDING
            ) AS interval_end
        FROM saving_contributions AS contribution
    ) AS contribution_intervals
        ON contribution_intervals.saving_goal_id = withdrawal_intervals.saving_goal_id
       AND contribution_intervals.interval_end > withdrawal_intervals.interval_start
       AND withdrawal_intervals.interval_end > contribution_intervals.interval_start;

    IF EXISTS (
        SELECT 1
        FROM saving_withdrawals AS withdrawal
        INNER JOIN migration_004_legacy_withdrawals AS legacy
            ON legacy.withdrawal_id = withdrawal.id
        LEFT JOIN tmp_withdrawal_allocation_candidate AS allocation
            ON allocation.withdrawal_id = withdrawal.id
        GROUP BY withdrawal.id, withdrawal.amount
        HAVING COALESCE(SUM(allocation.amount), 0) <> withdrawal.amount
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migration 004 stopped: a legacy withdrawal cannot be fully allocated.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM saving_contributions AS contribution
        INNER JOIN tmp_withdrawal_allocation_candidate AS allocation
            ON allocation.contribution_id = contribution.id
        GROUP BY contribution.id, contribution.amount
        HAVING SUM(allocation.amount) > contribution.amount
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migration 004 stopped: withdrawals exceed a contribution amount.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM saving_goals AS goal
        INNER JOIN (
            SELECT DISTINCT saving_goal_id
            FROM saving_withdrawals AS withdrawal
            INNER JOIN migration_004_legacy_withdrawals AS legacy
                ON legacy.withdrawal_id = withdrawal.id
        ) AS legacy_goal ON legacy_goal.saving_goal_id = goal.id
        LEFT JOIN (
            SELECT
                contribution.saving_goal_id,
                SUM(
                    CASE
                        WHEN LOWER(contribution.source) = 'manual'
                          OR (
                              LOWER(contribution.source) = 'income_allocation'
                              AND transaction_row.is_deleted = FALSE
                          )
                        THEN GREATEST(
                            contribution.amount - COALESCE(allocated.total_amount, 0),
                            0
                        )
                        ELSE 0
                    END
                ) AS computed_current_amount
            FROM saving_contributions AS contribution
            LEFT JOIN transactions AS transaction_row
                ON transaction_row.id = contribution.transaction_id
            LEFT JOIN (
                SELECT contribution_id, SUM(amount) AS total_amount
                FROM tmp_withdrawal_allocation_candidate
                GROUP BY contribution_id
            ) AS allocated ON allocated.contribution_id = contribution.id
            GROUP BY contribution.saving_goal_id
        ) AS computed ON computed.saving_goal_id = goal.id
        WHERE ABS(
            goal.current_amount - COALESCE(computed.computed_current_amount, 0)
        ) > 0.005
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migration 004 stopped: inferred ledger does not match current_amount.';
    END IF;

    -- Publish the validated legacy allocation set atomically. The exception
    -- handler rolls this transaction back if either statement fails.
    DELETE allocation
    FROM saving_withdrawal_allocations AS allocation
    INNER JOIN saving_withdrawals AS withdrawal
        ON withdrawal.id = allocation.withdrawal_id
    INNER JOIN migration_004_legacy_withdrawals AS legacy
        ON legacy.withdrawal_id = withdrawal.id;

    INSERT INTO saving_withdrawal_allocations (
        withdrawal_id,
        contribution_id,
        amount
    )
    SELECT
        candidate.withdrawal_id,
        candidate.contribution_id,
        candidate.amount
    FROM tmp_withdrawal_allocation_candidate AS candidate
    INNER JOIN saving_withdrawals AS withdrawal
        ON withdrawal.id = candidate.withdrawal_id
    INNER JOIN migration_004_legacy_withdrawals AS legacy
        ON legacy.withdrawal_id = withdrawal.id;

    COMMIT;
    DROP TEMPORARY TABLE IF EXISTS tmp_withdrawal_allocation_candidate;
END//
DELIMITER ;

CALL backfill_legacy_withdrawal_allocations();
DROP PROCEDURE IF EXISTS backfill_legacy_withdrawal_allocations;
DROP TABLE IF EXISTS migration_004_legacy_withdrawals;
