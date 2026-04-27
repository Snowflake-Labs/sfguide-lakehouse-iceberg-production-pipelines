# Snowflake: Dynamic Iceberg Tables (silver over CLD)

This chapter is the **next Snowflake hands-on** after [Snowflake CLD](snowflake-catalog-cld.md). You keep **bronze** in Glue (read through the catalog-linked database), then add **Snowflake-managed Dynamic Iceberg Tables** that refresh on a schedule using **Snowflake-managed Iceberg storage** (`EXTERNAL_VOLUME = SNOWFLAKE_MANAGED`) — no external volume or cloud storage setup required.

Use current Snowflake documentation as the source of truth: [Create dynamic Apache Iceberg tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-create-iceberg) and [CREATE DYNAMIC ICEBERG TABLE](https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table).

## Prerequisites

- **CLD path complete:** finish **[snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)** first — catalog integration, trust, linked DB, and reads on **`balloon_game_events`** (or your `SNOWFLAKE_LINKED_DATABASE_NAME`) before you generate or apply **§2** DT SQL. Quick narrative: [snowflake-catalog-cld.md](snowflake-catalog-cld.md).
- **Privileges:** role can `CREATE DATABASE` / `CREATE SCHEMA` (or use an existing silver database), `CREATE DYNAMIC ICEBERG TABLE`, and `USAGE` on the **warehouse**. No external volume privilege needed — Snowflake manages storage.
- **Tooling:** `snow sql` from a working connection ([Managing Snowflake connections](https://docs.snowflake.com/developer-guide/snowflake-cli/connecting/configure-connections)); **`.aws-config/glue-database.json`** after **`task bronze:glue-setup`** (same input as CLD SQL generation).

## 1. Configure env vars

Raw rows in bronze live in **`balloon_game_events.event`** as a JSON string. **`task dt:generate-sql`** emits **five** Dynamic Iceberg Tables matching the legacy RisingWave MVs (`mv_leaderboard`, `mv_balloon_color_stats`, `mv_realtime_scores`, `mv_balloon_colored_pops`, `mv_color_performance_trends` — see **`docs/implementing_data_pipeline.md`** and [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md)).

All DTs use `EXTERNAL_VOLUME = SNOWFLAKE_MANAGED` — storage is fully managed by Snowflake. The only env vars you may want to override are the silver database / schema and warehouse.

| Variable | Default | Purpose |
|----------|---------|---------|
| `SNOWFLAKE_SILVER_DATABASE` | `balloon_silver` | Native database for DT objects (not the CLD name). |
| `SNOWFLAKE_SILVER_SCHEMA` | `silver` | Schema for all silver DTs. |
| `SNOWFLAKE_WAREHOUSE` | `COMPUTE_WH` | Warehouse for refresh compute. |

Print hints (CLD + DT env reminders):

```bash
task snowflake:print-env-hints
```

## 2. Generate SQL (DT namespace)

Do **not** start here until **[snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)** passes — DT SQL reads bronze through the catalog-linked database, and **`task dt:generate-sql`** uses **`.aws-config/glue-database.json`** (same artifact as CLD generation). Regenerating **`01`** / **`02`** when your Glue or integration inputs change is covered in [snowflake-catalog-cld.md](snowflake-catalog-cld.md) and [snowflake/lab/README.md](../snowflake/lab/README.md) (**`task snowflake:generate-lab-sql`**); this chapter focuses on **`03`** only.

**Silver pipelines** (writes `snowflake/lab/generated/03_dt_pipelines.generated.sql` — all five DTs):

```bash
task dt:generate-sql
```

**Optional — one-shot** (regenerate **`01`**, **`02`**, and **`03`** together after broader env changes): `task snowflake:generate-lab-sql-all` or `uv run snowflake-lab-sql generate` — see [snowflake/lab/README.md](../snowflake/lab/README.md).

## 3. Apply in Snowflake

```bash
snow sql --connection <your_connection> --filename snowflake/lab/generated/03_dt_pipelines.generated.sql
```

**Pass:** all five `CREATE OR REPLACE DYNAMIC ICEBERG TABLE` statements succeed; `SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA` lists the objects; after refresh, `SELECT` returns rows.

**Common misses:** missing `USAGE` on warehouse; CLD identifiers mis-quoted for Glue; `SNOWFLAKE_MANAGED` storage requires account-level Snowflake-managed Iceberg storage to be available (confirm with your account admin if you get a storage permission error).

## 4. Verify with sample queries (manual test)

After DTs refresh, run read-only checks:

```bash
snow sql --connection <your_connection> --filename snowflake/lab/04_dt_verify_sample_queries.sql
```

Checklist and expected results: [snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md).

## 5. Scaffold without generator

Commented pointer: [snowflake/lab/03_dt_pipelines.sql](../snowflake/lab/03_dt_pipelines.sql). Verification samples (checked in): [snowflake/lab/04_dt_verify_sample_queries.sql](../snowflake/lab/04_dt_verify_sample_queries.sql).

## Related

- [snowflake-streamlit-sis.md](snowflake-streamlit-sis.md) — **next:** Streamlit in Snowflake over **`dt_*`**
- [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) — prerequisite QA before DT SQL
- [snowflake-catalog-cld.md](snowflake-catalog-cld.md) — catalog integration and CLD
- [snowflake/lab/README.md](../snowflake/lab/README.md) — `task snowflake:*` and `task dt:*`
- [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) — JSON keys and MV ↔ DT map
- [snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md) — short QA checklist
