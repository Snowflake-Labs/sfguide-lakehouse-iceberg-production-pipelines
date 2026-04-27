# DuckDB: Cross-Engine Iceberg via HIRC

This chapter is the **next hands-on** after [Snowflake Dynamic Iceberg Tables](snowflake-dynamic-iceberg-tables.md). You query the five silver Dynamic Iceberg Tables from **DuckDB** using Snowflake's **Horizon Iceberg REST Catalog (HIRC)** — no data copy, no ETL. DuckDB talks directly to Snowflake's Polaris-based REST catalog endpoint and reads Iceberg files from the external volume.

> **Public Preview:** HIRC is in Public Preview. Supported in all public Snowflake regions. No additional charges during preview.

---

## Prerequisites

- **Dynamic Iceberg Tables complete:** finish the [DT chapter](snowflake-dynamic-iceberg-tables.md) first — all five silver DTs (`dt_player_leaderboard`, `dt_balloon_color_stats`, `dt_realtime_scores`, `dt_balloon_colored_pops`, `dt_color_performance_trends`) must exist and return rows in `SNOWFLAKE_SILVER_DATABASE.silver`.
- **Tooling:** `snow` CLI connection working, `task` and `uv` on PATH, `uv sync` run from repo root.
- **Two HIRC rules to know before you start:**
  - Warehouse name in `ATTACH` must be **UPPERCASE** — `'BALLOON_SILVER'`, not `'balloon_silver'`. Lowercase returns HTTP 404.
  - `GRANT SELECT ON ALL TABLES` silently skips Dynamic Iceberg Tables — use `ON ALL DYNAMIC TABLES` and `ON FUTURE DYNAMIC TABLES` instead.

---

## 1. Configure env vars

Set these in `.env` (or export) before running setup tasks. Use your `LAB_USERNAME` as the prefix for workshop shared accounts.

| Variable | Workshop default | Purpose |
|----------|-----------------|---------|
| `SNOWFLAKE_ACCOUNT_URL` | `https://<org>-<account>.snowflakecomputing.com` | Snowflake account URL for HIRC endpoint |
| `SNOWFLAKE_SILVER_DATABASE` | `${LAB_USERNAME}_balloon_silver` | Silver database containing Dynamic Iceberg Tables |
| `SA_USER` | `${LAB_USERNAME}_duckdb_sa` | Service account user for DuckDB HIRC access |
| `SA_ROLE` | `${LAB_USERNAME}_duckdb_silver_reader` | Role granted to the service account |
| `PAT_NAME` | `{SA_USER}_PAT` (uppercased) | Name of the PAT stored in the OS keyring |

Example `.env` block (substitute your `LAB_USERNAME` — e.g. `ksampath`):

```bash
SNOWFLAKE_ACCOUNT_URL=https://<org>-<account>.snowflakecomputing.com
SA_USER=${LAB_USERNAME}_duckdb_sa
SA_ROLE=${LAB_USERNAME}_duckdb_silver_reader
SNOWFLAKE_SILVER_DATABASE=${LAB_USERNAME}_balloon_silver
```

Print hints for your current values:

```bash
task snowflake:print-env-hints
```

---

## 2. Quick Start

The fastest path: one task sets up the service account and PAT, one SQL block grants Iceberg access, then open the notebook.

**Step 1 — Create the service account, role, and PAT:**

```bash
task snowflake:pat-create
```

This calls `sfutils-pat create` which creates the role, user, and a PAT scoped to that role in one shot, then stores the PAT in your OS keyring. No `.env` paste required.

**Step 2 — Grant Iceberg access** (run as `ACCOUNTADMIN` — replace `balloon_silver` with your `SNOWFLAKE_SILVER_DATABASE`):

```sql
GRANT USAGE ON DATABASE balloon_silver TO ROLE duckdb_silver_reader;
GRANT USAGE ON SCHEMA balloon_silver.silver TO ROLE duckdb_silver_reader;
GRANT SELECT ON ALL DYNAMIC TABLES IN SCHEMA balloon_silver.silver TO ROLE duckdb_silver_reader;
GRANT SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA balloon_silver.silver TO ROLE duckdb_silver_reader;
```

**Pass:** `SHOW GRANTS TO ROLE duckdb_silver_reader` lists `SELECT` on each of the five DTs and `USAGE` on the database and schema.

**Step 3 — Open the notebook:**

Open `notebooks/duckdb_lab_guide.ipynb` in Jupyter or VS Code. The notebook:

1. Loads the PAT from the OS keyring (falls back to `SNOWFLAKE_PASSWORD` env var for CI)
2. Installs and loads the DuckDB `iceberg` and `httpfs` extensions
3. Creates the `iceberg_pat_secret` OAuth secret
4. Attaches the silver database via HIRC (`ATTACH 'BALLOON_SILVER' AS …`)
5. Discovers tables with `USE balloon_silver.SILVER; SHOW TABLES`
6. Queries all five silver DTs

Run each cell top-to-bottom. The notebook uses `%sql` magic from `jupysql`.

---

## 3. Manual path

This section walks through each step in detail for those who want full control or are running DuckDB SQL outside the notebook.

### What `task snowflake:pat-create` does

`task snowflake:pat-create` calls `sfutils-pat create --user SA_USER --role SA_ROLE --db SNOWFLAKE_SILVER_DATABASE`, which:

1. Creates the role `SA_ROLE` if it does not exist (no hyphens — HIRC requires underscore-only role names)
2. Creates the user `SA_USER` with `DEFAULT_ROLE = SA_ROLE`
3. Grants `SA_ROLE` to `SA_USER`
4. Creates a PAT scoped to `SA_ROLE` and stores it under `HOST:ACCOUNT:USER:SFUTILS-PAT:PAT_NAME` in your OS keyring (Keychain on macOS, Secret Service on Linux, Windows Credential Manager on Windows)

**Pass:** task exits 0; the PAT appears in `SHOW USER PROGRAMMATIC ACCESS TOKENS FOR USER <SA_USER>`.

> **Security:** The PAT lives in the OS keyring only. It is never written to `.env` or any tracked file. For CI/CD environments, inject the PAT at runtime from a vault or secrets manager.

### Manual service account SQL

If you need to create the role and user manually (e.g. to inspect or customise the SQL):

```sql
CREATE ROLE IF NOT EXISTS duckdb_silver_reader;

CREATE USER IF NOT EXISTS duckdb_sa
  DEFAULT_ROLE = duckdb_silver_reader
  DEFAULT_WAREHOUSE = COMPUTE_WH
  COMMENT = 'DuckDB HIRC service account';

GRANT ROLE duckdb_silver_reader TO USER duckdb_sa;

GRANT USAGE ON DATABASE balloon_silver TO ROLE duckdb_silver_reader;
GRANT USAGE ON SCHEMA balloon_silver.silver TO ROLE duckdb_silver_reader;

-- Required — ON ALL TABLES silently skips Dynamic Iceberg Tables:
GRANT SELECT ON ALL DYNAMIC TABLES IN SCHEMA balloon_silver.silver TO ROLE duckdb_silver_reader;
GRANT SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA balloon_silver.silver TO ROLE duckdb_silver_reader;
```

Replace `balloon_silver` and `duckdb_silver_reader` with your `SNOWFLAKE_SILVER_DATABASE` and `SA_ROLE` values.

### DuckDB SQL

Install and load extensions (once per DuckDB installation):

```sql
INSTALL iceberg;
INSTALL httpfs;
LOAD iceberg;
LOAD httpfs;
```

Create the PAT-based Iceberg secret (replace `<your_pat>`, `<account>`, and `duckdb_silver_reader` with your values):

```sql
CREATE SECRET iceberg_pat_secret (
    TYPE iceberg,
    CLIENT_ID '',
    CLIENT_SECRET '<your_pat>',
    OAUTH2_SERVER_URI 'https://<account>.snowflakecomputing.com/polaris/api/catalog/v1/oauth/tokens',
    OAUTH2_GRANT_TYPE 'client_credentials',
    OAUTH2_SCOPE 'session:role:duckdb_silver_reader'
);
```

Attach the silver database — catalog name must be **UPPERCASE**:

```sql
ATTACH 'BALLOON_SILVER' AS balloon_silver (
    TYPE iceberg,
    SECRET iceberg_pat_secret,
    ENDPOINT 'https://<account>.snowflakecomputing.com/polaris/api/catalog',
    SUPPORT_NESTED_NAMESPACES false
);
```

Discover tables (`SHOW ALL TABLES` returns empty for Iceberg REST catalogs — use `USE` first):

```sql
USE balloon_silver.SILVER;
SHOW TABLES;
```

Query silver DTs (table and column names from HIRC are uppercase):

```sql
SELECT player, total_score, bonus_pops, last_event_ts
FROM balloon_silver.SILVER.DT_PLAYER_LEADERBOARD
ORDER BY total_score DESC NULLS LAST
LIMIT 10;

SELECT balloon_color, total_pops, avg_score
FROM balloon_silver.SILVER.DT_BALLOON_COLOR_STATS
ORDER BY total_pops DESC
LIMIT 5;

SELECT window_start, window_end, player, window_score
FROM balloon_silver.SILVER.DT_REALTIME_SCORES
ORDER BY window_start DESC, window_score DESC
LIMIT 10;
```

**Pass:** each query returns rows; `SHOW TABLES` lists all five `DT_*` tables.

---

## 4. Known limitations

| Limitation | Detail |
|------------|--------|
| Read-only | External engines can query but cannot write to Iceberg tables via HIRC |
| Iceberg v2 only | HIRC exposes Iceberg v2 or earlier; v3 is not supported |
| Row/column policies | Tables with row access or masking policies are not accessible via HIRC |
| Snowflake-managed only | Externally managed Iceberg tables, Delta, and Parquet Direct are not exposed |
| `SHOW ALL TABLES` | Returns empty for Iceberg REST catalogs in DuckDB — use `USE catalog.SCHEMA; SHOW TABLES` |
| `information_schema` | Not available for attached Iceberg REST catalogs in DuckDB |
| Hyphens in role names | HIRC does not support hyphens in role names — use underscores |

---

## Related

- [Snowflake HIRC documentation](https://docs.snowflake.com/en/user-guide/tables-iceberg-open-catalog)
- [DuckDB Iceberg extension](https://duckdb.org/docs/extensions/iceberg/overview)
- [sfutils-pat](https://github.com/Snowflake-Labs/sfutils-pat) — PAT creation and keyring management
- [Snowflake Dynamic Iceberg Tables](snowflake-dynamic-iceberg-tables.md) — prerequisite chapter
