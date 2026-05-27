-- =============================================================================
-- DuckDB Service Account Setup (HIRC)
-- =============================================================================
-- Creates a service account with PAT for DuckDB Iceberg REST Catalog access.
-- Usage:
--   CALL setup_duckdb_service_account();           -- create user, role, network, PAT
--   CALL grant_duckdb_read_access();               -- grant SELECT on silver tables
--   CALL revoke_duckdb_read_access();              -- revoke SELECT on silver tables
--   CALL rotate_duckdb_pat();                      -- rotate the PAT
--   CALL cleanup_duckdb_service_account();         -- tear down everything
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE SUMMIT26_AR103_BALLOON_SILVER;
USE SCHEMA PUBLIC;

-- =============================================================================
-- SETUP PROCEDURE
-- =============================================================================
CREATE OR REPLACE PROCEDURE setup_duckdb_service_account(
  lab_database    VARCHAR DEFAULT 'SUMMIT26_AR103_BALLOON_SILVER',
  lab_schema      VARCHAR DEFAULT 'SILVER',
  sa_role         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SILVER_READER',
  sa_user         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA',
  sa_pat_name     VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA_PAT',
  np_name         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA_NP',
  nr_name         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA_NR',
  pat_days_expiry INT    DEFAULT 7
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  LET nr_fqn VARCHAR := lab_database || '.PUBLIC.' || nr_name;
  LET schema_fqn VARCHAR := lab_database || '.' || lab_schema;
  LET pat_comment VARCHAR := 'PAT for DuckDB HIRC access — restricted to ' || sa_role;
  LET pat_token_name VARCHAR;
  LET pat_token_secret VARCHAR;

  -- Step 1: Create the role
  EXECUTE IMMEDIATE 'CREATE ROLE IF NOT EXISTS ' || sa_role;

  -- Step 2: Create the service user
  EXECUTE IMMEDIATE 'CREATE USER IF NOT EXISTS ' || sa_user
    || ' TYPE = SERVICE DEFAULT_ROLE = ' || sa_role;

  -- Step 3: Grant the role to the user
  EXECUTE IMMEDIATE 'GRANT ROLE ' || sa_role || ' TO USER ' || sa_user;

  -- Step 4: Network rule and policy (open to all IPs for lab)
  EXECUTE IMMEDIATE 'CREATE NETWORK RULE IF NOT EXISTS ' || nr_fqn
    || ' MODE = INGRESS TYPE = IPV4 VALUE_LIST = (''0.0.0.0/0'')';

  EXECUTE IMMEDIATE 'CREATE NETWORK POLICY IF NOT EXISTS ' || np_name
    || ' ALLOWED_NETWORK_RULE_LIST = (''' || nr_fqn || ''')';

  EXECUTE IMMEDIATE 'ALTER USER ' || sa_user || ' SET NETWORK_POLICY = ' || np_name;

  -- Step 5: Generate the PAT and capture the token_secret
  LET pat_sql VARCHAR := 'ALTER USER ' || sa_user
    || ' ADD PROGRAMMATIC ACCESS TOKEN ' || sa_pat_name
    || ' ROLE_RESTRICTION = ' || sa_role
    || ' DAYS_TO_EXPIRY = ' || pat_days_expiry::VARCHAR
    || ' COMMENT = ''' || pat_comment || '''';
  LET rs RESULTSET := (EXECUTE IMMEDIATE :pat_sql);
  LET cur CURSOR FOR rs;
  OPEN cur;
  FETCH cur INTO :pat_token_name, :pat_token_secret;

  RETURN pat_token_secret;
END;

-- =============================================================================
-- GRANTS PROCEDURE
-- =============================================================================
CREATE OR REPLACE PROCEDURE grant_duckdb_read_access(
  lab_database    VARCHAR DEFAULT 'SUMMIT26_AR103_BALLOON_SILVER',
  lab_schema      VARCHAR DEFAULT 'SILVER',
  sa_role         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SILVER_READER'
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  LET schema_fqn VARCHAR := lab_database || '.' || lab_schema;

  EXECUTE IMMEDIATE 'GRANT USAGE ON DATABASE ' || lab_database || ' TO ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'GRANT USAGE ON SCHEMA ' || schema_fqn || ' TO ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'GRANT SELECT ON ALL DYNAMIC TABLES IN SCHEMA ' || schema_fqn || ' TO ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'GRANT SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA ' || schema_fqn || ' TO ROLE ' || sa_role;

  RETURN 'Granted read access on ' || schema_fqn || ' to role ' || sa_role;
END;

-- =============================================================================
-- REVOKE GRANTS PROCEDURE
-- =============================================================================
CREATE OR REPLACE PROCEDURE revoke_duckdb_read_access(
  lab_database    VARCHAR DEFAULT 'SUMMIT26_AR103_BALLOON_SILVER',
  lab_schema      VARCHAR DEFAULT 'SILVER',
  sa_role         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SILVER_READER'
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  LET schema_fqn VARCHAR := lab_database || '.' || lab_schema;

  EXECUTE IMMEDIATE 'REVOKE SELECT ON ALL DYNAMIC TABLES IN SCHEMA ' || schema_fqn || ' FROM ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'REVOKE SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA ' || schema_fqn || ' FROM ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'REVOKE USAGE ON SCHEMA ' || schema_fqn || ' FROM ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'REVOKE USAGE ON DATABASE ' || lab_database || ' FROM ROLE ' || sa_role;

  RETURN 'Revoked read access on ' || schema_fqn || ' from role ' || sa_role;
END;

-- =============================================================================
-- ROTATE PAT PROCEDURE
-- =============================================================================
CREATE OR REPLACE PROCEDURE rotate_duckdb_pat(
  sa_user         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA',
  sa_pat_name     VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA_PAT',
  sa_role         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SILVER_READER',
  pat_days_expiry INT    DEFAULT 7
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  LET pat_comment VARCHAR := 'PAT for DuckDB HIRC access — restricted to ' || sa_role;
  LET pat_token_name VARCHAR;
  LET pat_token_secret VARCHAR;

  EXECUTE IMMEDIATE 'ALTER USER ' || sa_user || ' REMOVE PROGRAMMATIC ACCESS TOKEN ' || sa_pat_name;

  LET pat_sql VARCHAR := 'ALTER USER ' || sa_user
    || ' ADD PROGRAMMATIC ACCESS TOKEN ' || sa_pat_name
    || ' ROLE_RESTRICTION = ' || sa_role
    || ' DAYS_TO_EXPIRY = ' || pat_days_expiry::VARCHAR
    || ' COMMENT = ''' || pat_comment || '''';
  LET rs RESULTSET := (EXECUTE IMMEDIATE :pat_sql);
  LET cur CURSOR FOR rs;
  OPEN cur;
  FETCH cur INTO :pat_token_name, :pat_token_secret;

  RETURN pat_token_secret;
END;

-- =============================================================================
-- CLEANUP PROCEDURE
-- =============================================================================
CREATE OR REPLACE PROCEDURE cleanup_duckdb_service_account(
  lab_database    VARCHAR DEFAULT 'SUMMIT26_AR103_BALLOON_SILVER',
  lab_schema      VARCHAR DEFAULT 'SILVER',
  sa_role         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SILVER_READER',
  sa_user         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA',
  sa_pat_name     VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA_PAT',
  np_name         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA_NP',
  nr_name         VARCHAR DEFAULT 'SUMMIT26_AR103_DUCKDB_SA_NR'
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  LET nr_fqn VARCHAR := lab_database || '.PUBLIC.' || nr_name;
  LET schema_fqn VARCHAR := lab_database || '.' || lab_schema;

  EXECUTE IMMEDIATE 'REVOKE SELECT ON ALL DYNAMIC TABLES IN SCHEMA ' || schema_fqn || ' FROM ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'REVOKE SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA ' || schema_fqn || ' FROM ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'REVOKE USAGE ON SCHEMA ' || schema_fqn || ' FROM ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'REVOKE USAGE ON DATABASE ' || lab_database || ' FROM ROLE ' || sa_role;
  EXECUTE IMMEDIATE 'REVOKE ROLE ' || sa_role || ' FROM USER ' || sa_user;
  EXECUTE IMMEDIATE 'ALTER USER ' || sa_user || ' REMOVE PROGRAMMATIC ACCESS TOKEN ' || sa_pat_name;
  EXECUTE IMMEDIATE 'ALTER USER ' || sa_user || ' UNSET NETWORK_POLICY';
  EXECUTE IMMEDIATE 'DROP NETWORK POLICY IF EXISTS ' || np_name;
  EXECUTE IMMEDIATE 'DROP NETWORK RULE IF EXISTS ' || nr_fqn;
  EXECUTE IMMEDIATE 'DROP USER IF EXISTS ' || sa_user;
  EXECUTE IMMEDIATE 'DROP ROLE IF EXISTS ' || sa_role;

  RETURN 'Cleanup complete — all resources removed.';
END;

-- =============================================================================
-- RUN: Create the service account (uncomment to execute)
-- =============================================================================
-- CALL setup_duckdb_service_account();
-- CALL grant_duckdb_read_access();
-- CALL revoke_duckdb_read_access();
-- CALL rotate_duckdb_pat();
-- CALL cleanup_duckdb_service_account();
