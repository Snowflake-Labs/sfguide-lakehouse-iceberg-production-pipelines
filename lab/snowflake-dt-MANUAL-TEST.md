# Manual test plan — Dynamic Iceberg Tables (silver)

Use after [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) passes. Full narrative: [snowflake-dynamic-iceberg-tables.md](snowflake-dynamic-iceberg-tables.md).

**Storage:** DTs use `EXTERNAL_VOLUME = SNOWFLAKE_MANAGED` — no external volume or S3/IAM setup needed.

**Defaults in this doc:** silver database **`balloon_silver`**, schema **`silver`** (override if you set `SNOWFLAKE_SILVER_DATABASE` / `SNOWFLAKE_SILVER_SCHEMA`). **Sample queries:** checked-in script [snowflake/lab/04_dt_verify_sample_queries.sql](../snowflake/lab/04_dt_verify_sample_queries.sql) — run with `snow sql --filename snowflake/lab/04_dt_verify_sample_queries.sql` after DTs have had time to refresh ([Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-about) monitoring in Snowflake docs).

## Preconditions

- [ ] CLD reads work per [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) (bronze `balloon_game_events` visible through the linked database).
- [ ] `.aws-config/glue-database.json` present (same artifact **`task dt:generate-sql`** uses for Glue identifier quoting).
- [ ] Valid **`snow`** connection ([Managing Snowflake connections](https://docs.snowflake.com/developer-guide/snowflake-cli/connecting/configure-connections)).

## Env configuration (do this first)

Align **`.env`** (or exports) with [snowflake-dynamic-iceberg-tables.md §1](snowflake-dynamic-iceberg-tables.md#1-configure-env-vars). Only the silver database/schema and warehouse need setting (all have defaults):

- [ ] **`SNOWFLAKE_SILVER_DATABASE`**, **`SNOWFLAKE_SILVER_SCHEMA`**, **`SNOWFLAKE_WAREHOUSE`** — match what you want in generated `03` SQL (defaults: `balloon_silver`, `silver`, `COMPUTE_WH`).

```bash
task snowflake:print-env-hints
```

## Phase A — Dynamic Iceberg Tables

### A1. Generate DT SQL

`task dt:generate-sql`

**Pass:** `snowflake/lab/generated/03_dt_pipelines.generated.sql` exists; each DT block has `EXTERNAL_VOLUME = SNOWFLAKE_MANAGED` and no `BASE_LOCATION`; the bronze table FQN inside the file matches your CLD (`<linked_db>."<glue_db_lower>"."balloon_game_events"`).

### A2. Apply DT SQL

`snow sql --filename snowflake/lab/generated/03_dt_pipelines.generated.sql`

**Pass:** five `CREATE OR REPLACE DYNAMIC ICEBERG TABLE` statements complete without errors.

### A3. Discovery

```sql
USE DATABASE balloon_silver;
USE SCHEMA silver;
SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA;
```

**Pass:** five rows: `dt_player_leaderboard`, `dt_balloon_color_stats`, `dt_realtime_scores`, `dt_balloon_colored_pops`, `dt_color_performance_trends`. If state is not yet active, wait for `TARGET_LAG` refresh per Snowflake docs, then re-check.

### A4. Sample reads (per table)

Run the bundled script (recommended), or paste blocks below.

**A4a — Leaderboard**

```sql
SELECT player, total_score, bonus_pops, last_event_ts
FROM balloon_silver.silver.dt_player_leaderboard
ORDER BY total_score DESC NULLS LAST
LIMIT 15;
```

**Pass:** One row per `player` from bronze; `total_score` / `bonus_pops` non-null where bronze had data; `last_event_ts` is the max event time for that player.

**A4b — Per player × color**

```sql
SELECT player, balloon_color, balloon_pops, points_by_color, bonus_hits, last_event_ts
FROM balloon_silver.silver.dt_balloon_color_stats
ORDER BY player, points_by_color DESC NULLS LAST
LIMIT 20;
```

**Pass:** `(player, balloon_color)` unique; counts and sums align with intuition from raw pops.

**A4c — 15s window scores**

```sql
SELECT player, total_score, window_start, window_end
FROM balloon_silver.silver.dt_realtime_scores
ORDER BY window_start DESC, player
LIMIT 20;
```

**Pass:** `window_end` equals `DATEADD(second, 15, window_start)` for each row; multiple players can share the same `window_start`.

**A4d — Windowed pops by color**

```sql
SELECT player, balloon_color, balloon_pops, window_start, window_end
FROM balloon_silver.silver.dt_balloon_colored_pops
ORDER BY window_start DESC, player, balloon_color
LIMIT 20;
```

**Pass:** Same 15s window semantics as **A4c**; dimensions include color.

**A4e — Color performance by window**

```sql
SELECT balloon_color, avg_score_per_pop, total_pops, window_start, window_end
FROM balloon_silver.silver.dt_color_performance_trends
ORDER BY window_start DESC, balloon_color
LIMIT 20;
```

**Pass:** `avg_score_per_pop` is a finite average; `total_pops` ≥ 1 for populated windows.

### A5. Window span sanity (all windowed DTs)

```sql
SELECT
  'dt_realtime_scores' AS tbl,
  COUNT_IF(window_end <> DATEADD(second, 15, window_start)) AS bad_spans
FROM balloon_silver.silver.dt_realtime_scores
UNION ALL
SELECT 'dt_balloon_colored_pops', COUNT_IF(window_end <> DATEADD(second, 15, window_start))
FROM balloon_silver.silver.dt_balloon_colored_pops
UNION ALL
SELECT 'dt_color_performance_trends', COUNT_IF(window_end <> DATEADD(second, 15, window_start))
FROM balloon_silver.silver.dt_color_performance_trends;
```

**Pass:** `bad_spans = 0` for all three (empty tables yield 0 rows — then skip or load more bronze first).

### A6. Optional — bronze parity (leaderboard row count)

Edit the FQN to match your catalog-linked database and **lowercase** Glue schema (same as `02_cld_verify` / `SHOW SCHEMAS`).

```sql
SELECT
  (SELECT COUNT(*) FROM balloon_silver.silver.dt_player_leaderboard) AS dt_players,
  (
    SELECT COUNT(DISTINCT PARSE_JSON(event):player::STRING)
    FROM balloon_game_events."<glue_db_lower>"."balloon_game_events"
  ) AS bronze_distinct_players;
```

**Pass (steady state):** `dt_players = bronze_distinct_players` when every distinct player has at least one event in bronze. If DT is still refreshing, retry after a short wait.

### A7. One-shot script

From repo root:

```bash
snow sql --connection <your_connection> --filename snowflake/lab/04_dt_verify_sample_queries.sql
```

Edit **`04_dt_verify_sample_queries.sql`** `USE DATABASE` / `USE SCHEMA` if you overrode defaults. Uncomment and fix the optional bronze block at the bottom for parity.

## Next — Streamlit in Snowflake

After DTs refresh and verify queries pass, see **[snowflake-streamlit-sis.md](snowflake-streamlit-sis.md)** to deploy with **`snow streamlit deploy`** (or stage + **`CREATE STREAMLIT`**) so the SiS app reads **`balloon_silver.silver.dt_*`**, then go **live** if your account requires it.

## Failure notes

- **Warehouse:** grant `USAGE` on the warehouse named in the generated `03` script (default `COMPUTE_WH` or `SNOWFLAKE_WAREHOUSE`).
- **SNOWFLAKE_MANAGED storage:** if your account does not have Snowflake-managed Iceberg storage enabled, contact your account admin. This is a feature that may require account-level enablement.
- **Empty windowed DTs:** ensure bronze load has events spanning more than one 15-second bucket, or widen the time range in bronze load; otherwise window aggregates may be empty even when leaderboard has rows.
