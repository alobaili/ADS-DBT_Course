"""
The same capstone pipeline, expressed as Dagster assets.

This is the identical work the Airflow DAG does. Only the way of describing it
changes, and that difference is the whole point of the comparison.

Airflow asks: what tasks should run, and in what order?
Dagster asks:  what tables should exist, and what does each one need?

So the Airflow file names tasks, `ingest_csv` and `transform`. This file names
the things those tasks produce, `service_requests_csv` and `dbt_marts`, and lets
Dagster work out the order from what each asset depends on. Nothing here says
"run ingest before transform". Dagster knows, because `dbt_marts` declares that
it needs the three landed tables.

The practical payoff is that you can rebuild one table and everything downstream
of it, without describing that subset by hand. The cost is that a job which is
genuinely a sequence of actions, rather than a set of tables, fits less neatly.

Each asset shells out to the same run_step.py the Airflow DAG uses, so the two
orchestrators are compared fairly: identical work, different description.
"""
import json
import os
import re
import subprocess

# Note: do NOT add `from __future__ import annotations` to this file. It turns
# every type hint into a string, and Dagster checks the type of the `context`
# parameter at runtime. The resulting error claims that AssetExecutionContext
# must be annotated with AssetExecutionContext, which is true but not helpful.

from dagster import (
    AssetExecutionContext,
    Definitions,
    MetadataValue,
    Output,
    RetryPolicy,
    ScheduleDefinition,
    asset,
    define_asset_job,
)

COURSE_PYTHON = os.getenv("COURSE_PYTHON", "/opt/course/.venv/bin/python")
COURSE_STEPS = os.getenv("COURSE_STEPS", "/opt/course/labs/day5/reference/run_step.py")

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# The API is the only step that reaches outside the stack, so it is the only one
# that needs a generous retry policy.
API_RETRIES = RetryPolicy(max_retries=5, delay=15)
DEFAULT_RETRIES = RetryPolicy(max_retries=3, delay=30)


def run_step(context: AssetExecutionContext, step: str) -> dict:
    """
    Run one pipeline step and return what it reported.

    The step prints a single RESULT line as JSON. Parsing that back gives us
    real numbers to attach to the asset, so the Dagster UI shows how many rows
    each table actually holds rather than just a green tick.
    """
    command = [COURSE_PYTHON, COURSE_STEPS, step]
    context.log.info("running: %s", " ".join(command))

    env = dict(os.environ)
    completed = subprocess.run(command, capture_output=True, text=True, env=env)
    output = ANSI.sub("", completed.stdout + completed.stderr)

    if completed.returncode != 0:
        context.log.error(output[-2000:])
        raise RuntimeError(f"step {step} failed with exit code {completed.returncode}")

    for line in output.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):])
    return {}


def _metadata(result: dict) -> dict:
    """Turn a step's result dictionary into metadata the Dagster UI can show."""
    return {k: MetadataValue.text(str(v)) for k, v in result.items()}


# ---------------------------------------------------------------------------
# Ingestion assets. No dependencies, so Dagster runs these three in parallel.
# ---------------------------------------------------------------------------
@asset(
    group_name="ingest",
    description="Raw service request extract landed from CSV.",
    retry_policy=DEFAULT_RETRIES,
    compute_kind="python",
)
def service_requests_csv(context: AssetExecutionContext) -> Output[None]:
    result = run_step(context, "ingest_csv")
    return Output(None, metadata=_metadata(result))


@asset(
    group_name="ingest",
    description="District budget and headcount, read from the finance workbook.",
    retry_policy=DEFAULT_RETRIES,
    compute_kind="python",
)
def district_budgets(context: AssetExecutionContext) -> Output[None]:
    result = run_step(context, "ingest_excel")
    return Output(None, metadata=_metadata(result))


@asset(
    group_name="ingest",
    description="Public holiday reference feed, fetched over HTTP.",
    retry_policy=API_RETRIES,
    compute_kind="api",
)
def public_holidays(context: AssetExecutionContext) -> Output[None]:
    result = run_step(context, "ingest_api")
    return Output(None, metadata=_metadata(result))


# ---------------------------------------------------------------------------
# Transformation. Depends on all three landed tables, so it waits for them.
# ---------------------------------------------------------------------------
@asset(
    group_name="transform",
    deps=[service_requests_csv, district_budgets, public_holidays],
    description="Staging, intermediate and mart models built by dbt.",
    retry_policy=DEFAULT_RETRIES,
    compute_kind="dbt",
)
def dbt_marts(context: AssetExecutionContext) -> Output[None]:
    result = run_step(context, "transform")
    return Output(None, metadata=_metadata(result))


# ---------------------------------------------------------------------------
# Machine learning and reporting.
# ---------------------------------------------------------------------------
@asset(
    group_name="ml",
    deps=[dbt_marts],
    description="SLA predictions for every request, including open ones.",
    retry_policy=DEFAULT_RETRIES,
    compute_kind="scikit-learn",
)
def sla_predictions(context: AssetExecutionContext) -> Output[None]:
    result = run_step(context, "score")
    return Output(None, metadata=_metadata(result))


@asset(
    group_name="ml",
    deps=[sla_predictions],
    description="Summary of the run for the service manager.",
    compute_kind="python",
)
def pipeline_report(context: AssetExecutionContext) -> Output[None]:
    result = run_step(context, "report")
    return Output(None, metadata=_metadata(result))


# ---------------------------------------------------------------------------
# A job over every asset, and a schedule to match the Airflow DAG.
# ---------------------------------------------------------------------------
capstone_job = define_asset_job(name="capstone_job", selection="*")

daily_schedule = ScheduleDefinition(
    job=capstone_job,
    cron_schedule="0 2 * * *",
    execution_timezone="UTC",
)

defs = Definitions(
    assets=[
        service_requests_csv,
        district_budgets,
        public_holidays,
        dbt_marts,
        sla_predictions,
        pipeline_report,
    ],
    jobs=[capstone_job],
    schedules=[daily_schedule],
)
