-- =============================================================================
-- DuckDB Service Account Setup (HIRC)
-- =============================================================================
-- Adjust the variables below, then run the full script.
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- =============================================================================
-- VARIABLES: Change these to match your environment
-- =============================================================================
SET lab_database    = 'SUMMIT26_AR103_BALLOON_SILVER';
SET lab_schema      = 'SILVER';
SET sa_role         = 'SUMMIT26_AR103_DUCKDB_SILVER_READER';
SET sa_user         = 'SUMMIT26_AR103_DUCKDB_SA';
SET sa_pat_name     = 'SUMMIT26_AR103_DUCKDB_SA_PAT';
SET np_name         = 'SUMMIT26_AR103_DUCKDB_SA_NP';
SET nr_name         = 'SUMMIT26_AR103_DUCKDB_SA_NR';
SET pat_days_expiry = 7;

-- =============================================================================
-- SETUP: Create role, user, network policy, and PAT
-- =============================================================================

-- Step 1: Create the role
CREATE ROLE IF NOT EXISTS IDENTIFIER($sa_role);

-- Step 2: Create the service user with the role as default
CREATE USER IF NOT EXISTS IDENTIFIER($sa_user)
  TYPE = SERVICE
  DEFAULT_ROLE = $sa_role;

-- Step 3: Grant the role to the service user
GRANT ROLE IDENTIFIER($sa_role) TO USER IDENTIFIER($sa_user);

-- Step 4: Create a network rule and network policy (open to all IPs for lab)
CREATE OR REPLACE NETWORK RULE IDENTIFIER($lab_database || '.PUBLIC.' || $nr_name)
  MODE = INGRESS
  TYPE = IPV4
  VALUE_LIST = ('0.0.0.0/0');

CREATE OR REPLACE NETWORK POLICY IDENTIFIER($np_name)
  ALLOWED_NETWORK_RULE_LIST = ($lab_database || '.PUBLIC.' || $nr_name);

ALTER USER IDENTIFIER($sa_user)
  SET NETWORK_POLICY = $np_name;

-- Step 5: Generate the PAT restricted to the role
ALTER USER IDENTIFIER($sa_user) ADD PROGRAMMATIC ACCESS TOKEN IDENTIFIER($sa_pat_name)
  ROLE_RESTRICTION = $sa_role
  DAYS_TO_EXPIRY = $pat_days_expiry
  COMMENT = 'PAT for DuckDB HIRC access — restricted to ' || $sa_role;

-- =============================================================================
-- GRANTS: Allow the role to read from the silver schema
-- =============================================================================

-- GRANT USAGE ON DATABASE IDENTIFIER($lab_database) TO ROLE IDENTIFIER($sa_role);
-- GRANT USAGE ON SCHEMA IDENTIFIER($lab_database || '.' || $lab_schema) TO ROLE IDENTIFIER($sa_role);
-- GRANT SELECT ON ALL DYNAMIC TABLES IN SCHEMA IDENTIFIER($lab_database || '.' || $lab_schema) TO ROLE IDENTIFIER($sa_role);
-- GRANT SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA IDENTIFIER($lab_database || '.' || $lab_schema) TO ROLE IDENTIFIER($sa_role);

-- =============================================================================
-- ROTATE (Optional): Drop and recreate PAT
-- =============================================================================

-- ALTER USER IDENTIFIER($sa_user) REMOVE PROGRAMMATIC ACCESS TOKEN IDENTIFIER($sa_pat_name);
-- ALTER USER IDENTIFIER($sa_user) ADD PROGRAMMATIC ACCESS TOKEN IDENTIFIER($sa_pat_name)
--   ROLE_RESTRICTION = $sa_role
--   DAYS_TO_EXPIRY = $pat_days_expiry
--   COMMENT = 'PAT for DuckDB HIRC access — restricted to ' || $sa_role;

-- =============================================================================
-- CLEANUP (Optional): Tear down everything
-- =============================================================================

-- REVOKE SELECT ON ALL DYNAMIC TABLES IN SCHEMA IDENTIFIER($lab_database || '.' || $lab_schema) FROM ROLE IDENTIFIER($sa_role);
-- REVOKE SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA IDENTIFIER($lab_database || '.' || $lab_schema) FROM ROLE IDENTIFIER($sa_role);
-- REVOKE USAGE ON SCHEMA IDENTIFIER($lab_database || '.' || $lab_schema) FROM ROLE IDENTIFIER($sa_role);
-- REVOKE USAGE ON DATABASE IDENTIFIER($lab_database) FROM ROLE IDENTIFIER($sa_role);
-- REVOKE ROLE IDENTIFIER($sa_role) FROM USER IDENTIFIER($sa_user);
-- ALTER USER IDENTIFIER($sa_user) REMOVE PROGRAMMATIC ACCESS TOKEN IDENTIFIER($sa_pat_name);
-- ALTER USER IDENTIFIER($sa_user) UNSET NETWORK_POLICY;
-- DROP NETWORK POLICY IF EXISTS IDENTIFIER($np_name);
-- DROP NETWORK RULE IF EXISTS IDENTIFIER($lab_database || '.PUBLIC.' || $nr_name);
-- DROP USER IF EXISTS IDENTIFIER($sa_user);
-- DROP ROLE IF EXISTS IDENTIFIER($sa_role);
