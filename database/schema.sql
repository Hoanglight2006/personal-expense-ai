-- =============================================================================
-- PERSONAL EXPENSE AI — FULL CONSOLIDATED DATABASE SCHEMA (MySQL 8.0)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS personal_expense
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE personal_expense;

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. CATEGORIES TABLE
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_normalized VARCHAR(150) NULL,
    icon VARCHAR(30) NOT NULL DEFAULT 'other',
    color VARCHAR(20) NOT NULL DEFAULT '#6366F1',
    type ENUM('income', 'expense') NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    CONSTRAINT fk_categories_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_categories_user (user_id),
    INDEX idx_categories_user_type (user_id, type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. TRANSACTIONS TABLE
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    type ENUM('income', 'expense') NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    description VARCHAR(255) NULL,
    transaction_date DATE NOT NULL,
    payment_method ENUM('cash', 'bank_transfer') NOT NULL DEFAULT 'cash',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    CONSTRAINT fk_transactions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_transactions_category_owner FOREIGN KEY (category_id, user_id) REFERENCES categories(id, user_id) ON DELETE CASCADE,
    CONSTRAINT ck_transaction_amount_positive CHECK (amount > 0),
    INDEX idx_transactions_user_date (user_id, transaction_date),
    INDEX idx_transactions_user_deleted (user_id, is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. BUDGETS TABLE
CREATE TABLE IF NOT EXISTS budgets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    month SMALLINT NOT NULL,
    year SMALLINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_budgets_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_budgets_category_owner FOREIGN KEY (category_id, user_id) REFERENCES categories(id, user_id) ON DELETE CASCADE,
    CONSTRAINT uq_budget_user_category_period UNIQUE (user_id, category_id, month, year),
    CONSTRAINT ck_budget_amount_positive CHECK (amount > 0),
    CONSTRAINT ck_budget_month_range CHECK (month >= 1 AND month <= 12),
    INDEX idx_budgets_user_period (user_id, year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. SAVING GOALS TABLE
CREATE TABLE IF NOT EXISTS saving_goals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    target_amount DECIMAL(15, 2) NOT NULL,
    current_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    deadline DATE NULL,
    status ENUM('active', 'completed', 'cancelled') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_saving_goals_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT ck_saving_goal_target_positive CHECK (target_amount > 0),
    CONSTRAINT ck_saving_goal_current_non_negative CHECK (current_amount >= 0),
    INDEX idx_saving_goals_user (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. SAVING CONTRIBUTIONS TABLE
CREATE TABLE IF NOT EXISTS saving_contributions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    saving_goal_id INT NOT NULL,
    transaction_id INT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    source ENUM('income_allocation', 'manual') NOT NULL,
    note VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_saving_contrib_goal FOREIGN KEY (saving_goal_id) REFERENCES saving_goals(id) ON DELETE CASCADE,
    CONSTRAINT fk_saving_contrib_txn FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL,
    CONSTRAINT ck_contribution_amount_positive CHECK (amount > 0),
    INDEX idx_saving_contrib_goal (saving_goal_id),
    INDEX idx_saving_contrib_txn (transaction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. SAVING WITHDRAWALS TABLE
CREATE TABLE IF NOT EXISTS saving_withdrawals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    saving_goal_id INT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    note VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_saving_withdrawals_goal FOREIGN KEY (saving_goal_id) REFERENCES saving_goals(id) ON DELETE CASCADE,
    CONSTRAINT ck_withdrawal_amount_positive CHECK (amount > 0),
    INDEX idx_saving_withdrawals_goal (saving_goal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. SAVING WITHDRAWAL ALLOCATIONS TABLE
CREATE TABLE IF NOT EXISTS saving_withdrawal_allocations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    withdrawal_id INT NOT NULL,
    contribution_id INT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    CONSTRAINT fk_withdrawal_alloc_withdrawal FOREIGN KEY (withdrawal_id) REFERENCES saving_withdrawals(id) ON DELETE CASCADE,
    CONSTRAINT fk_withdrawal_alloc_contrib FOREIGN KEY (contribution_id) REFERENCES saving_contributions(id) ON DELETE CASCADE,
    CONSTRAINT ck_allocation_amount_positive CHECK (amount > 0),
    INDEX idx_withdrawal_alloc_contrib (contribution_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. AI REPORTS TABLE
CREATE TABLE IF NOT EXISTS ai_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    month SMALLINT NOT NULL,
    year SMALLINT NOT NULL,
    report_type ENUM('monthly_summary', 'budget_suggestion', 'chat_answer') NOT NULL,
    content TEXT NOT NULL,
    meta_data JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ai_reports_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_ai_reports_user_period (user_id, year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
