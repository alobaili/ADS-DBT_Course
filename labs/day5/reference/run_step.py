"""
Command line entry point for every pipeline step.

Why the pipeline is driven through a command line rather than by importing the
functions into the orchestrator:

Airflow 2.10 requires SQLAlchemy 1.4, and this course pins SQLAlchemy 2.0. Both
constraints are real and neither can be moved, so the orchestrator and the task
cannot share one Python environment. Running each step as a subprocess in its
own environment removes the conflict completely.

That is not a workaround, it is the normal arrangement in production. It also
buys two things worth having. Any step can be run by hand, exactly as the
scheduler runs it, which makes debugging a matter of copying one line. And the
pipeline can be moved between orchestrators without touching the task code,
which is what lets the same steps run under both Airflow and Dagster today.

Usage:
    python run_step.py ingest_csv
    python run_step.py ingest_excel
    python run_step.py ingest_api      [--url URL] [--fallback PATH]
    python run_step.py transform       [--project-dir DIR]
    python run_step.py score
    python run_step.py report

Every step exits 0 on success and non-zero on failure, which is the only signal
an orchestrator actually needs.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingestion as ing  # noqa: E402
import scoring  # noqa: E402

LOG = logging.getLogger("run_step")

# dbt writes colour escape codes even when piped.
ANSI = re.compile(r"\x1b\[[0-9;]*m")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

DEFAULT_CSV = REPO / "data" / "raw" / "service_requests_raw.csv"
DEFAULT_XLSX = REPO / "labs" / "day5" / "sources" / "district_budgets.xlsx"
DEFAULT_FIXTURE = REPO / "services" / "mock_api" / "public_holidays.json"
DEFAULT_DBT = REPO / "labs" / "day4" / "solutions" / "dbt_project_solution"

API_URL = os.getenv("HOLIDAYS_API_URL", "http://localhost:8000/holidays")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")


def _engine():
    return ing.make_engine(host=PG_HOST)


def step_ingest_csv(args) -> dict:
    df = ing.read_csv_source(args.path or DEFAULT_CSV)
    rows = ing.land(df, "service_requests_csv", _engine())
    return {"step": "ingest_csv", "rows": rows}


def step_ingest_excel(args) -> dict:
    df = ing.read_excel_budgets(args.path or DEFAULT_XLSX)
    rows = ing.land(df, "district_budgets", _engine())
    return {"step": "ingest_excel", "rows": rows, "quarters": int(df["quarter"].nunique())}


def step_ingest_api(args) -> dict:
    df = ing.read_holidays_api(args.url or API_URL, args.fallback or DEFAULT_FIXTURE)
    rows = ing.land(df, "public_holidays", _engine())
    return {"step": "ingest_api", "rows": rows, "source": str(df["source"].iloc[0])}


def step_transform(args) -> dict:
    """Run dbt. The orchestrator's job is to call it, not to reimplement it."""
    project = Path(args.project_dir or DEFAULT_DBT)
    env = dict(os.environ, DBT_PROFILES_DIR=str(project), POSTGRES_HOST=PG_HOST)
    result = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "build"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )
    # dbt colours its output, so strip the escape codes before reporting them.
    clean = ANSI.sub("", result.stdout)
    tail = clean.strip().splitlines()[-1:] or [""]
    if result.returncode != 0:
        LOG.error("dbt build failed:\n%s", clean[-2000:])
        raise RuntimeError("dbt build failed")
    return {"step": "transform", "dbt": tail[0].strip()}


def step_score(args) -> dict:
    metrics = scoring.train_and_score(_engine())
    return {"step": "score", **metrics}


def step_report(args) -> dict:
    """
    Summarise what the pipeline produced.

    This is the step a service manager would actually read, and it is the reason
    the whole graph exists.
    """
    engine = _engine()
    q = """
        select
            count(*)                                            as scored_rows,
            sum(is_open)                                        as open_requests,
            round(avg(predicted_probability)::numeric, 4)       as mean_probability,
            sum(case when is_open = 1 and predicted_sla_met = 0
                     then 1 else 0 end)                         as open_at_risk
        from analytics_ml.sla_predictions
    """
    df = ing.read_database_table(engine, q)
    return {"step": "report", **{k: (int(v) if v is not None and float(v) == int(float(v)) else float(v))
                                 for k, v in df.iloc[0].items()}}


STEPS = {
    "ingest_csv": step_ingest_csv,
    "ingest_excel": step_ingest_excel,
    "ingest_api": step_ingest_api,
    "transform": step_transform,
    "score": step_score,
    "report": step_report,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one step of the Day 5 pipeline.")
    parser.add_argument("step", choices=sorted(STEPS))
    parser.add_argument("--path", help="override the source file path")
    parser.add_argument("--url", help="override the API url")
    parser.add_argument("--fallback", help="override the offline fixture path")
    parser.add_argument("--project-dir", help="override the dbt project directory")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        result = STEPS[args.step](args)
    except Exception as exc:
        LOG.error("step %s failed: %s", args.step, exc)
        return 1

    print("RESULT " + json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
