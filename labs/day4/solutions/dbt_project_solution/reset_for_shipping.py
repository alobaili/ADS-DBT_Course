"""
Reset the course environment after smoke testing, before capturing the VM image.

Removes BOTH kinds of contamination:
  1. dbt build artefacts inside the project folders (target/, logs/, etc.)
  2. the schemas dbt built in Postgres, which are the real leak risk

Leaves the Day 1 to 3 state untouched: schema `raw` and its five tables.

    python reset_for_shipping.py           # show what would be removed
    python reset_for_shipping.py --apply   # actually remove it
"""
import os, shutil, sys
from pathlib import Path
from sqlalchemy import create_engine, text

APPLY = "--apply" in sys.argv
ROOT = Path(__file__).resolve().parent

ARTEFACTS = ["target", "logs", "dbt_packages", "package-lock.yml"]
PROJECTS = ["dbt_project", "dbt_project_solution"]
BUILT_SCHEMAS = ["analytics_staging", "analytics_intermediate",
                 "analytics_marts", "analytics_seeds", "snapshots"]

print("DRY RUN (pass --apply to act)\n" if not APPLY else "APPLYING\n")

# --- 1. folder artefacts --------------------------------------------------
for proj in PROJECTS:
    base = ROOT / proj
    if not base.exists():
        continue
    for a in ARTEFACTS:
        p = base / a
        if p.exists():
            print(f"  remove  {proj}/{a}")
            if APPLY:
                shutil.rmtree(p) if p.is_dir() else p.unlink()

# --- 2. schemas dbt built -------------------------------------------------
url = "postgresql+psycopg2://{u}:{p}@{h}:{P}/{d}".format(
    u=os.getenv("POSTGRES_USER", "ads_dbt"),
    p=os.getenv("POSTGRES_PASSWORD", "ads_dbt_password"),
    h=os.getenv("POSTGRES_HOST", "localhost"),
    P=os.getenv("POSTGRES_PORT", "5432"),
    d=os.getenv("POSTGRES_DB", "ads_dbt_analytics"))
engine = create_engine(url)

try:
    engine.connect().close()
except Exception:
    print("\n  Could not reach Postgres on "
          + os.getenv("POSTGRES_HOST", "localhost") + ":5432.")
    print("  Start it first:  docker compose up -d")
    print("  Folder artefacts above were handled; schemas were NOT.")
    sys.exit(1)

with engine.begin() as conn:
    present = [r[0] for r in conn.execute(text(
        "select schema_name from information_schema.schemata "
        "where schema_name = any(:s)"), {"s": BUILT_SCHEMAS})]
    for s in present:
        print(f"  drop    schema {s}")
        if APPLY:
            conn.execute(text(f'drop schema "{s}" cascade'))

    # --- 3. confirm the Day 1 to 3 state survived -------------------------
    print("\n  Day 1 to 3 state (must be intact):")
    for t in ["service_requests", "services", "channels", "districts", "departments"]:
        n = conn.execute(text(f"select count(*) from raw.{t}")).scalar()
        print(f"    raw.{t:<18} {n:>7,} rows")

print("\nDone." if APPLY else "\nNothing changed. Re-run with --apply.")
