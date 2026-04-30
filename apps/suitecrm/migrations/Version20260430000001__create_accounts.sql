-- Doctrine-style migration: create canonical CRM accounts table.
CREATE TABLE IF NOT EXISTS accounts (
  id              VARCHAR(36)    NOT NULL,
  name            VARCHAR(150)   NOT NULL,
  industry        VARCHAR(50)    NULL,
  annual_revenue  DECIMAL(18, 2) NULL,
  email           VARCHAR(254)   NULL,
  created_at      DATETIME       NOT NULL,
  updated_at      DATETIME       NOT NULL,
  CONSTRAINT PRIMARY PRIMARY KEY (id),
  CONSTRAINT uq_accounts_email UNIQUE (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
