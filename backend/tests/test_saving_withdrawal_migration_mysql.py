import os
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.api.routes.transactions import _recomputed_goal_current_amount
from app.config import settings


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MYSQL_MIGRATION_TEST") != "1",
    reason="Set RUN_MYSQL_MIGRATION_TEST=1 to run against a disposable MySQL database.",
)

MIGRATION_FILE = Path(__file__).parents[1] / "migrations" / "004_saving_withdrawals.sql"


def migration_statements(script: str):
    delimiter = ";"
    buffer: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("DELIMITER "):
            delimiter = stripped.split(maxsplit=1)[1]
            continue
        buffer.append(line)
        combined = "\n".join(buffer).rstrip()
        if combined.endswith(delimiter):
            statement = combined[: -len(delimiter)].strip()
            if statement:
                yield statement
            buffer = []
    assert not "\n".join(buffer).strip(), "Migration contains an unterminated statement"


@contextmanager
def disposable_mysql_database():
    configured_url = make_url(settings.DATABASE_URL)
    if not configured_url.drivername.startswith("mysql"):
        pytest.skip("Configured DATABASE_URL is not MySQL.")

    database_name = f"withdrawal_migration_test_{uuid4().hex[:12]}"
    server_engine = create_engine(
        configured_url.set(database=None), isolation_level="AUTOCOMMIT"
    )
    database_engine = None
    try:
        with server_engine.connect() as connection:
            connection.exec_driver_sql(
                f"CREATE DATABASE `{database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
        database_engine = create_engine(
            configured_url.set(database=database_name),
            isolation_level="AUTOCOMMIT",
        )
        yield database_engine
    finally:
        if database_engine is not None:
            database_engine.dispose()
        try:
            with server_engine.connect() as connection:
                connection.exec_driver_sql(f"DROP DATABASE IF EXISTS `{database_name}`")
        finally:
            server_engine.dispose()


def create_saving_base_schema(connection):
    statements = (
        """
        CREATE TABLE transactions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE saving_goals (
            id INT PRIMARY KEY AUTO_INCREMENT,
            target_amount NUMERIC(15, 2) NOT NULL,
            current_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            status ENUM('ACTIVE', 'COMPLETED', 'CANCELLED') NOT NULL DEFAULT 'ACTIVE',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE saving_contributions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            saving_goal_id INT NOT NULL,
            transaction_id INT NULL,
            amount NUMERIC(15, 2) NOT NULL,
            source ENUM('INCOME_ALLOCATION', 'MANUAL') NOT NULL,
            note VARCHAR(255) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_test_contribution_goal
                FOREIGN KEY (saving_goal_id) REFERENCES saving_goals(id) ON DELETE CASCADE,
            CONSTRAINT fk_test_contribution_transaction
                FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
        ) ENGINE=InnoDB
        """,
    )
    for statement in statements:
        connection.exec_driver_sql(statement)


def run_migration(connection):
    script = MIGRATION_FILE.read_text(encoding="utf-8")
    for statement in migration_statements(script):
        connection.exec_driver_sql(statement)


def test_004_creates_fresh_schema_and_is_retry_safe():
    with disposable_mysql_database() as engine:
        with engine.connect() as connection:
            create_saving_base_schema(connection)
            run_migration(connection)
            run_migration(connection)

            tables = {
                row[0]
                for row in connection.exec_driver_sql(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE()"
                )
            }
            assert "saving_withdrawals" in tables
            assert "saving_withdrawal_allocations" in tables
            assert "migration_004_legacy_withdrawals" not in tables
            columns = {
                row[0]
                for row in connection.exec_driver_sql(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() "
                    "AND table_name = 'saving_withdrawals'"
                )
            }
            assert "idempotency_key" in columns


def test_004_retry_preserves_public_key_that_matches_legacy_pattern():
    with disposable_mysql_database() as engine:
        with engine.connect() as connection:
            create_saving_base_schema(connection)
            run_migration(connection)

            connection.exec_driver_sql(
                "INSERT INTO saving_goals "
                "(id, target_amount, current_amount, status) "
                "VALUES (1, 100000.00, 30000.00, 'ACTIVE')"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_contributions "
                "(id, saving_goal_id, transaction_id, amount, source) VALUES "
                "(1, 1, NULL, 50000.00, 'MANUAL'), "
                "(2, 1, NULL, 50000.00, 'MANUAL')"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_withdrawals "
                "(id, saving_goal_id, amount, idempotency_key) VALUES "
                "(1, 1, 50000.00, 'normal-key'), "
                "(2, 1, 20000.00, 'legacy-2')"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_withdrawal_allocations "
                "(withdrawal_id, contribution_id, amount) VALUES "
                "(1, 1, 50000.00), "
                "(2, 2, 20000.00)"
            )

            run_migration(connection)

            allocations = connection.exec_driver_sql(
                "SELECT withdrawal_id, contribution_id, amount "
                "FROM saving_withdrawal_allocations "
                "ORDER BY withdrawal_id, contribution_id"
            ).all()
            assert [
                (withdrawal_id, contribution_id, Decimal(str(amount)))
                for withdrawal_id, contribution_id, amount in allocations
            ] == [
                (1, 1, Decimal("50000.00")),
                (2, 2, Decimal("20000.00")),
            ]


def test_004_backfills_draft_and_preserves_trash_restore_amount():
    with disposable_mysql_database() as engine:
        with engine.connect() as connection:
            create_saving_base_schema(connection)
            connection.exec_driver_sql(
                """
                CREATE TABLE saving_withdrawals (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    saving_goal_id INT NOT NULL,
                    amount NUMERIC(15, 2) NOT NULL,
                    note VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_test_withdrawal_goal
                        FOREIGN KEY (saving_goal_id) REFERENCES saving_goals(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                """
            )
            connection.exec_driver_sql(
                "INSERT INTO transactions (id, is_deleted) VALUES (1, FALSE)"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_goals "
                "(id, target_amount, current_amount, status) "
                "VALUES (1, 100000.00, 50000.00, 'COMPLETED')"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_contributions "
                "(id, saving_goal_id, transaction_id, amount, source) "
                "VALUES (1, 1, 1, 100000.00, 'INCOME_ALLOCATION')"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_withdrawals "
                "(id, saving_goal_id, amount, note) "
                "VALUES (1, 1, 50000.00, 'Legacy withdrawal')"
            )

            run_migration(connection)
            run_migration(connection)

            withdrawal = connection.exec_driver_sql(
                "SELECT idempotency_key FROM saving_withdrawals WHERE id = 1"
            ).scalar_one()
            assert withdrawal == "legacy-1"
            allocated = connection.exec_driver_sql(
                "SELECT SUM(amount) FROM saving_withdrawal_allocations "
                "WHERE withdrawal_id = 1"
            ).scalar_one()
            assert Decimal(str(allocated)) == Decimal("50000.00")

            with Session(bind=connection) as session:
                connection.exec_driver_sql(
                    "UPDATE transactions SET is_deleted = TRUE WHERE id = 1"
                )
                session.expire_all()
                assert _recomputed_goal_current_amount(session, 1) == Decimal("0.00")

                connection.exec_driver_sql(
                    "UPDATE transactions SET is_deleted = FALSE WHERE id = 1"
                )
                session.expire_all()
                assert _recomputed_goal_current_amount(session, 1) == Decimal("50000.00")


def test_004_stops_when_draft_current_amount_cannot_be_inferred_safely():
    with disposable_mysql_database() as engine:
        with engine.connect() as connection:
            create_saving_base_schema(connection)
            connection.exec_driver_sql(
                """
                CREATE TABLE saving_withdrawals (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    saving_goal_id INT NOT NULL,
                    amount NUMERIC(15, 2) NOT NULL,
                    note VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_test_unsafe_withdrawal_goal
                        FOREIGN KEY (saving_goal_id) REFERENCES saving_goals(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                """
            )
            connection.exec_driver_sql(
                "INSERT INTO transactions (id, is_deleted) VALUES (1, FALSE)"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_goals "
                "(id, target_amount, current_amount, status) "
                "VALUES (1, 100000.00, 60000.00, 'ACTIVE')"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_contributions "
                "(id, saving_goal_id, transaction_id, amount, source) "
                "VALUES (1, 1, 1, 100000.00, 'INCOME_ALLOCATION')"
            )
            connection.exec_driver_sql(
                "INSERT INTO saving_withdrawals "
                "(id, saving_goal_id, amount) VALUES (1, 1, 50000.00)"
            )

            with pytest.raises(DBAPIError, match="inferred ledger does not match current_amount"):
                run_migration(connection)

            allocation_count = connection.exec_driver_sql(
                "SELECT COUNT(*) FROM saving_withdrawal_allocations"
            ).scalar_one()
            assert allocation_count == 0

            connection.exec_driver_sql(
                "UPDATE saving_goals SET current_amount = 50000.00 WHERE id = 1"
            )
            run_migration(connection)

            allocated = connection.exec_driver_sql(
                "SELECT SUM(amount) FROM saving_withdrawal_allocations "
                "WHERE withdrawal_id = 1"
            ).scalar_one()
            assert Decimal(str(allocated)) == Decimal("50000.00")
