"""
The capstone pipeline as an Airflow DAG.

The whole week runs as one scheduled graph:

    ingest_csv  ─┐
    ingest_excel ┼─> transform (dbt) ─> score (ML) ─> report
    ingest_api  ─┘

The three ingest tasks have no dependency on each other, so Airflow runs them in
parallel. Everything after them is a straight line, because each step needs the
one before it to have finished.

Each task is a BashOperator that calls run_step.py in the course virtual
environment. Airflow requires SQLAlchemy 1.4 and the course pins SQLAlchemy 2.0,
so the orchestrator and the task genuinely cannot share one environment. Running
each step as a subprocess removes the conflict and means every task can be
reproduced by hand by copying the command out of the log.
"""
from __future__ import annotations

import os
from datetime import timedelta

import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

# Where the course lives. Set these in the Airflow environment rather than
# hard-coding them, so the same DAG works on the VM and on your own machine.
COURSE_PYTHON = os.getenv("COURSE_PYTHON", "/opt/course/.venv/bin/python")
COURSE_STEPS = os.getenv("COURSE_STEPS", "/opt/course/labs/day5/reference/run_step.py")

RUN = f"{COURSE_PYTHON} {COURSE_STEPS}"

default_args = {
    "owner": "analytics",
    # Retries are the single most valuable setting here. A transient network
    # failure on the API task should not fail the whole pipeline, and a step
    # that is safe to re-run costs nothing to retry.
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=20),
}

with DAG(
    dag_id="ads_dbt_pipeline",
    description="Raw sources to dbt marts to an SLA prediction, end to end",
    default_args=default_args,
    # Every night at 02:00. The data arrives overnight, so there is nothing to
    # gain from running earlier and a lot to lose from running during the day.
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2025, 3, 1, tz="UTC"),
    # Do not run fourteen months of history the moment the DAG is switched on.
    catchup=False,
    # One run at a time. Two concurrent runs would write to the same tables.
    max_active_runs=1,
    tags=["ads-dbt", "capstone", "day5"],
) as dag:

    start = EmptyOperator(task_id="start")

    # ---- Ingest: three independent sources, run in parallel ----------------
    ingest_csv = BashOperator(
        task_id="ingest_csv",
        bash_command=f"{RUN} ingest_csv",
    )

    ingest_excel = BashOperator(
        task_id="ingest_excel",
        bash_command=f"{RUN} ingest_excel",
    )

    ingest_api = BashOperator(
        task_id="ingest_api",
        bash_command=f"{RUN} ingest_api",
        # The API is the only task that depends on something outside our
        # control, so it gets more patience than the others.
        retries=5,
        retry_delay=timedelta(seconds=15),
    )

    # ---- Transform: dbt builds staging, intermediate and marts -------------
    transform = BashOperator(
        task_id="transform",
        bash_command=f"{RUN} transform",
    )

    # ---- Score: train and write predictions back to the warehouse ---------
    score = BashOperator(
        task_id="score",
        bash_command=f"{RUN} score",
    )

    # ---- Report: the summary a service manager would read -----------------
    report = BashOperator(
        task_id="report",
        bash_command=f"{RUN} report",
    )

    finish = EmptyOperator(task_id="finish")

    # The dependency graph. A list on the left means "all of these must finish
    # before the next task starts".
    start >> [ingest_csv, ingest_excel, ingest_api] >> transform >> score >> report >> finish
