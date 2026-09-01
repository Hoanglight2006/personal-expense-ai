import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.config import settings


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MYSQL_MIGRATION_TEST") != "1",
    reason="Set RUN_MYSQL_MIGRATION_TEST=1 to run against a disposable MySQL database.",
)

MIGRATION_FILE = Path(__file__).parents[2] / "database" / "migrations" / "001_category_management.sql"


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


def create_legacy_schema(connection):
    statements = (
        """
        CREATE TABLE users (
            id INT PRIMARY KEY AUTO_INCREMENT
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE categories (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            name VARCHAR(50) NOT NULL,
            type ENUM('INCOME', 'EXPENSE') NOT NULL,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_category_user FOREIGN KEY (user_id) REFERENCES users(id),
            CONSTRAINT uq_category_user_name_type UNIQUE (user_id, name, type)
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE transactions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            category_id INT NOT NULL,
            type ENUM('INCOME', 'EXPENSE') NOT NULL,
            amount NUMERIC(15, 2) NOT NULL,
            description VARCHAR(255),
            transaction_date DATE NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_transaction_user FOREIGN KEY (user_id) REFERENCES users(id),
            CONSTRAINT fk_transaction_category FOREIGN KEY (category_id)
                REFERENCES categories(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE budgets (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            category_id INT NOT NULL,
            amount NUMERIC(15, 2) NOT NULL,
            month SMALLINT NOT NULL,
            year SMALLINT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_budget_user FOREIGN KEY (user_id) REFERENCES users(id),
            CONSTRAINT fk_budget_category FOREIGN KEY (category_id)
                REFERENCES categories(id) ON DELETE CASCADE,
            CONSTRAINT uq_budget_user_category_period
                UNIQUE (user_id, category_id, month, year)
        ) ENGINE=InnoDB
        """,
    )
    for statement in statements:
        connection.exec_driver_sql(statement)


def test_migration_merges_legacy_duplicates_and_is_retry_safe():
    configured_url = make_url(settings.DATABASE_URL)
    if not configured_url.drivername.startswith("mysql"):
        pytest.skip("Configured DATABASE_URL is not MySQL.")

    database_name = f"category_migration_test_{uuid4().hex[:12]}"
    server_engine = create_engine(configured_url.set(database=None), isolation_level="AUTOCOMMIT")
    database_engine = None
    try:
        with server_engine.connect() as connection:
            connection.exec_driver_sql(
                f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )

        database_engine = create_engine(
            configured_url.set(database=database_name),
            isolation_level="AUTOCOMMIT",
        )
        with database_engine.connect() as connection:
            create_legacy_schema(connection)
            connection.exec_driver_sql("INSERT INTO users (id) VALUES (1)")
            connection.exec_driver_sql(
                "INSERT INTO categories (id, user_id, name, type) VALUES "
                "(10, 1, 'Khác', 'INCOME'), (11, 1, ' Khác ', 'EXPENSE')"
            )
            connection.exec_driver_sql(
                "INSERT INTO transactions "
                "(user_id, category_id, type, amount, transaction_date) VALUES "
                "(1, 10, 'INCOME', 5.00, '2026-08-01'), "
                "(1, 11, 'EXPENSE', 7.00, '2026-08-02')"
            )
            connection.exec_driver_sql(
                "INSERT INTO budgets (user_id, category_id, amount, month, year) VALUES "
                "(1, 10, 100.00, 8, 2026), (1, 11, 150.00, 8, 2026)"
            )

            script = MIGRATION_FILE.read_text(encoding="utf-8")
            for _ in range(2):
                for statement in migration_statements(script):
                    connection.exec_driver_sql(statement)

            assert connection.exec_driver_sql("SELECT COUNT(*) FROM categories").scalar_one() == 1
            assert connection.exec_driver_sql(
                "SELECT COUNT(DISTINCT category_id) FROM transactions"
            ).scalar_one() == 1
            budget = connection.exec_driver_sql(
                "SELECT COUNT(*), SUM(amount) FROM budgets"
            ).one()
            assert budget[0] == 1
            assert str(budget[1]) == "250.00"

            constraints = {
                row[0]
                for row in connection.exec_driver_sql(
                    "SELECT constraint_name FROM information_schema.table_constraints "
                    "WHERE constraint_schema = DATABASE()"
                )
            }
            assert "uq_category_user_normalized_name" in constraints
            assert "fk_transaction_category_owner" in constraints
            assert "fk_budget_category_owner" in constraints
    finally:
        if database_engine is not None:
            database_engine.dispose()
        try:
            with server_engine.connect() as connection:
                connection.exec_driver_sql(f"DROP DATABASE IF EXISTS `{database_name}`")
        finally:
            server_engine.dispose()
