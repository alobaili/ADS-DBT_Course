"""
Load the teaching dataset into Postgres so every notebook, and later dbt,
reads from one source of truth.

Run from PowerShell once Postgres is up (docker compose up -d):
    python seed_postgres.py
"""
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

HOST = os.getenv("POSTGRES_HOST", "localhost")
PORT = os.getenv("POSTGRES_PORT", "5432")
USER = os.getenv("POSTGRES_USER", "ads_dbt")
PWD = os.getenv("POSTGRES_PASSWORD", "ads_dbt_password")
DB = os.getenv("POSTGRES_DB", "ads_dbt_analytics")

engine = create_engine(f"postgresql+psycopg2://{USER}:{PWD}@{HOST}:{PORT}/{DB}")
DATA = Path(__file__).resolve().parent / "data"

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))

# Raw messy fact table lands in schema raw, exactly as received (all text-safe)
raw = pd.read_csv(DATA / "raw" / "service_requests_raw.csv", dtype=str)
raw.to_sql("service_requests", engine, schema="raw", if_exists="replace", index=False)
print(f"raw.service_requests: {len(raw):,} rows")

# Clean dimensions land in schema raw as typed seeds
for name in ["services", "channels", "districts", "departments"]:
    d = pd.read_csv(DATA / "seeds" / f"{name}.csv")
    d.to_sql(name, engine, schema="raw", if_exists="replace", index=False)
    print(f"raw.{name}: {len(d):,} rows")

print("Seed complete. Inspect at http://localhost:8081 (Adminer).")
