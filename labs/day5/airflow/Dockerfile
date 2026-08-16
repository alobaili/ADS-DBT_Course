# Airflow image carrying its own copy of the course environment.
#
# The two environments are kept apart on purpose. Airflow requires
# SQLAlchemy 1.4 and this course pins 2.0, so installing the course
# requirements into Airflow's Python would break one or the other.
# Instead the course stack lives in its own virtual environment at
# /opt/course/.venv and the DAG shells out to it.
FROM apache/airflow:2.10.5-python3.12

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements.txt /tmp/course-requirements.txt

# A separate virtual environment, isolated from Airflow's own dependencies.
# Built at /opt/venv, NOT under /opt/course: the compose bind mount overlays
# /opt/course with the host folder at runtime, which would hide this venv and
# expose the host's Windows .venv instead. There is no bin/python in that.
USER root
RUN mkdir -p /opt/venv && chown airflow: /opt/venv
USER airflow
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/course-requirements.txt \
 && /opt/venv/bin/pip install --no-cache-dir openpyxl==3.1.5 requests==2.32.3
