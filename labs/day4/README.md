# Day 4 — Data Transformation, Modelling and dbt

Additive drop-in for the existing `ADS-DBT_Course` tree. Nothing here replaces a
Day 1–3 file. Root-stack changes: **none** (dbt was already pinned in
`requirements.txt` on Day 1).

## What goes where

| From this folder | Into the course tree |
|---|---|
| `slides_guides/*` | `slides_guides/` |
| `dbt/dbt_project/` | `dbt_project/`  (delegate skeleton, TODOs) |
| `dbt/dbt_project_solution/` | `dbt_project_solution/`  (instructor) |
| `dbt/vendor/` | `vendor/`  (offline `dbt_utils`) |
| `dbt/simulate_sla_revision.py` | course root |

Strip `dbt_project_solution/`, both Word documents and this README before the
delegate handover.

## Verified state

Built and tested against live Postgres 16.14, `dbt-core 1.10.22`,
`dbt-postgres 1.10.2`.

```
dbt build --profiles-dir .
Done. PASS=54  WARN=1  ERROR=0
```

The single warning is `assert_resolution_after_submission`, downgraded
deliberately with its justification written into the test file. 21 objects,
12,000 rows through staging, fact and ML mart.

## Prerequisites on the day

```
docker compose up -d
cd dbt_project
dbt deps          # resolves offline from ../vendor/dbt_utils
dbt debug
```

`dbt deps` needs no network. To use the package hub instead, swap the commented
block in `packages.yml` and delete `package-lock.yml` before rerunning.

To demonstrate the Snowflake or BigQuery walkthrough live, install the adapter
in advance: `pip install dbt-snowflake` or `pip install dbt-bigquery`. Neither
is required for the course itself.
