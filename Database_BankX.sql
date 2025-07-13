CREATE DATABASE IF NOT EXISTS bank_app;
USE bank_app;

-- USERS TABLE
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(100),
    age INT,
    gender VARCHAR(10),
    occupation VARCHAR(50),
    ini_deposit FLOAT,
    city VARCHAR(50),
    state VARCHAR(50)
);

-- ACCOUNTS TABLE
DROP TABLE IF EXISTS accounts;
CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    balance FLOAT DEFAULT 0,
    account_type VARCHAR(50),
    account_number VARCHAR(20) UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- TRIGGER: Auto-generate account_number before insert
DELIMITER $$

CREATE TRIGGER set_account_number_before_insert
BEFORE INSERT ON accounts
FOR EACH ROW
BEGIN
    IF NEW.account_number IS NULL THEN
        SET NEW.account_number = LEFT(REPLACE(UUID(), '-', ''), 10);
    END IF;
END$$

DELIMITER ;

-- TRANSACTIONS TABLE
DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    from_account INT,
    to_account INT,
    amount FLOAT,
    transaction_type VARCHAR(20), -- deposit, withdrawal, transfer
    date DATE DEFAULT (CURRENT_DATE),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_account) REFERENCES accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (to_account) REFERENCES accounts(account_id) ON DELETE CASCADE
);

-- View all tables (optional testing)
SELECT * FROM users;
SELECT * FROM accounts;
SELECT * FROM transactions;


