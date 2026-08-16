# Build your pipeline here

This folder is where you build the pipeline during Lab 1 and Lab 2. It starts
empty on purpose. The Build Workbook takes you through it step by step, and
each step tells you what you should see when it works.

By the end of the day this folder will hold:

    ingestion.py    the four source readers, with retries and error handling
    scoring.py      the machine learning step
    run_step.py     the command line entry point the orchestrator calls

## If you get stuck

A finished version of every file is in `../reference/`. Use it to compare
against your own work when something will not run, rather than as a starting
point. You will learn far more from a broken file you fix than a working file
you copied.

## Running your own version instead of the reference

The stack is configured to run the reference implementation out of the box, so
the demonstration works before you have written anything. Once your own files
are complete, point the orchestrator at them by changing one environment
variable in `docker-compose.yml`:

    COURSE_STEPS: /opt/course/labs/day5/pipeline/run_step.py

Then restart the container:

    docker compose up -d --force-recreate airflow

EXPECT the Airflow UI at http://localhost:8080 to show the same DAG, now
running your code. If a task fails, open its log: the command it ran is printed
at the top, and you can paste that exact command into a terminal to reproduce
the failure outside Airflow.
