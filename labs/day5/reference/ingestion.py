"""
Multi-source ingestion for the Day 5 pipeline.

Four sources, one landing schema. Each reader is a small function with a clear
signature, a docstring and one job, so the orchestrator can call it as a task
and so it can be tested on its own.

Sources
    CSV        the raw service request extract, as on Day 1
    Excel      the district budget workbook from the finance team
    Database   the marts built by dbt on Day 4
    API        the public holiday feed, over real HTTP

Everything lands in the schema `raw_day5`, which keeps Day 5 ingestion separate
from the Day 1 `raw` schema so neither day can break the other.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

LOG = logging.getLogger("ingestion")

LANDING_SCHEMA = "raw_day5"

# Sheets in the budget workbook that hold data. "Notes" is prose, not data,
# so "read every sheet" would be wrong.
BUDGET_SHEETS = ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1"]


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
def make_engine(
    host: str = "localhost",
    port: int = 5432,
    user: str = "ads_dbt",
    password: str = "ads_dbt_password",
    database: str = "ads_dbt_analytics",
) -> Engine:
    """Return a SQLAlchemy engine for the course database."""
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url)


# ---------------------------------------------------------------------------
# Source 1: CSV
# ---------------------------------------------------------------------------
def read_csv_source(path: str | Path) -> pd.DataFrame:
    """
    Read the raw service request extract.

    Everything is read as text. The raw layer's job is to land what arrived,
    not to interpret it, which is the same rule the dbt staging layer follows.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV source not found: {path}")
    df = pd.read_csv(path, dtype=str)
    LOG.info("read_csv_source: %s rows from %s", len(df), path.name)
    return df


# ---------------------------------------------------------------------------
# Source 2: Excel
# ---------------------------------------------------------------------------
def _parse_currency(value: Any) -> float | None:
    """Turn 'SAR 412,000' into 412000.0. Returns None if it cannot be parsed."""
    if pd.isna(value):
        return None
    cleaned = str(value).replace("SAR", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        LOG.warning("_parse_currency: could not parse %r", value)
        return None


def read_excel_budgets(
    path: str | Path, sheets: list[str] | None = None
) -> pd.DataFrame:
    """
    Read the district budget workbook into one tidy frame.

    The workbook is shaped for human readers, so this function has to undo four
    things: three rows of preamble above the header, a blank spacer column, a
    TOTAL row at the foot of every sheet, and budgets stored as text.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel source not found: {path}")

    sheets = sheets or BUDGET_SHEETS
    frames = []

    for sheet in sheets:
        # The real header is row 4 of the sheet, so three rows are skipped.
        df = pd.read_excel(path, sheet_name=sheet, skiprows=3)

        # Drop the blank spacer column, whichever position it landed in.
        df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")])

        df = df.rename(
            columns={
                "District": "district_name",
                "Operating Budget": "operating_budget",
                "Headcount": "headcount",
            }
        )

        # The TOTAL row is a summary, not an observation.
        df = df[df["district_name"].astype(str).str.upper() != "TOTAL"]

        df["operating_budget"] = df["operating_budget"].apply(_parse_currency)
        df["headcount"] = pd.to_numeric(df["headcount"], errors="coerce")
        df["quarter"] = sheet

        frames.append(df[["quarter", "district_name", "operating_budget", "headcount"]])

    out = pd.concat(frames, ignore_index=True)
    LOG.info("read_excel_budgets: %s rows across %s sheets", len(out), len(sheets))
    return out


# ---------------------------------------------------------------------------
# Source 3: Database
# ---------------------------------------------------------------------------
def read_database_table(engine: Engine, query: str) -> pd.DataFrame:
    """Run a SQL query and return the result. Used to read the Day 4 marts."""
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    LOG.info("read_database_table: %s rows", len(df))
    return df


# ---------------------------------------------------------------------------
# Source 4: API
# ---------------------------------------------------------------------------
def fetch_json(
    url: str,
    timeout: float = 5.0,
    retries: int = 3,
    backoff: float = 1.0,
    headers: dict[str, str] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """
    GET a JSON document, retrying on failures that are worth retrying.

    Three failure modes are handled separately because they need different
    responses:

      * a transport failure or a 5xx is usually temporary, so retry
      * a 4xx means the request itself is wrong, so retry is pointless
      * a 200 carrying invalid JSON is a real and easily missed case, because
        the status code says everything is fine

    Waits grow with each attempt, so a service that is briefly overloaded is
    not hammered by every delegate at once.
    """
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout, headers=headers or {})

            if 400 <= response.status_code < 500:
                # Not worth retrying: the request will fail the same way again.
                raise requests.HTTPError(
                    f"{response.status_code} client error for {url}"
                )

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as exc:
            if "client error" in str(exc):
                LOG.error("fetch_json: %s, not retrying", exc)
                raise
            last_error = exc
            LOG.warning("fetch_json: attempt %s failed: %s", attempt, exc)

        except json.JSONDecodeError as exc:
            last_error = exc
            LOG.warning(
                "fetch_json: attempt %s returned 200 with invalid JSON: %s",
                attempt,
                exc,
            )

        except requests.RequestException as exc:
            last_error = exc
            LOG.warning("fetch_json: attempt %s transport error: %s", attempt, exc)

        if attempt < retries:
            wait = backoff * attempt
            LOG.info("fetch_json: waiting %.1fs before retry", wait)
            sleep(wait)

    raise RuntimeError(f"fetch_json: all {retries} attempts failed for {url}") from last_error


def read_holidays_api(url: str, fallback_path: str | Path | None = None) -> pd.DataFrame:
    """
    Fetch the public holiday feed, falling back to the bundled fixture.

    The fallback exists so the pipeline still runs when the feed is unreachable.
    A pipeline that stops because a reference feed is down is more fragile than
    one that carries on with yesterday's copy and says so loudly.
    """
    try:
        payload = fetch_json(url)
        source = "api"
    except Exception as exc:
        if fallback_path is None:
            raise
        LOG.warning("read_holidays_api: falling back to fixture because: %s", exc)
        payload = json.loads(Path(fallback_path).read_text(encoding="utf-8"))
        source = "fixture"

    df = pd.DataFrame(payload["holidays"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["source"] = source
    LOG.info("read_holidays_api: %s holidays from %s", len(df), source)
    return df


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------
def land(df: pd.DataFrame, table: str, engine: Engine, schema: str = LANDING_SCHEMA) -> int:
    """
    Write a frame into the landing schema, replacing what was there.

    Replace rather than append is what makes the whole pipeline safe to re-run:
    running it twice gives the same result as running it once. That property is
    called idempotency and the orchestration section depends on it.
    """
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    df.to_sql(table, engine, schema=schema, if_exists="replace", index=False)
    LOG.info("land: %s rows into %s.%s", len(df), schema, table)
    return len(df)
