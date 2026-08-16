# Dagster image, built the same way as the Airflow one so the comparison
# between the two orchestrators is fair: identical task code, identical
# isolation, only the orchestration layer differs.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir dagster==1.13.16 dagster-webserver==1.13.16

COPY requirements.txt /tmp/course-requirements.txt

# Built at /opt/venv, NOT under /opt/course: the compose bind mount overlays
# /opt/course with the host folder at runtime, which would hide this venv and
# expose the host's Windows .venv instead. There is no bin/python in that.
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/course-requirements.txt \
 && /opt/venv/bin/pip install --no-cache-dir openpyxl==3.1.5 requests==2.32.3

WORKDIR /opt/course
