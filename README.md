# Applied Data Science & Machine Learning with Python and dbt

Course workspace. One repository carries the whole five-day
programme: notebooks, labs, the shared Postgres database, the dbt project,
and the Day 5 orchestration stack.

**Environment convention for this course**
- Editor: **VS Code**
- Notebooks: **Jupyter**, run inside VS Code
- Terminal: **Windows PowerShell** for every command shown
- Heavier tooling (Postgres, dbt, Airflow, Dagster): **Docker**
- Language: **Python native.** A few notebook cells show a Java equivalent
  only where it helps you map a concept. This is not a Java course.

---

## One-time setup

You need Docker Desktop and VS Code (with the Python and Jupyter extensions).

```powershell
# 1. Clone and enter the repo
cd C:\ADS-DBT_Course      # delegate VM
# (instructor local: cd E:\ADS-DBT_Course)

# 2. Copy the environment file
Copy-Item .env.example .env

# 3. Start Postgres (our single source of truth) and Adminer
docker compose up -d

# 4. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 5. Install the Python stack
pip install -r requirements.txt

# 6. Generate the teaching dataset, then load it into Postgres
python data\generate_dataset.py
python seed_postgres.py
```

Check the database loaded: open <http://localhost:8081> (Adminer), system
PostgreSQL, server `postgres`, user `ads_dbt`, password `ads_dbt_password`,
database `ads_dbt_analytics`.

> Prefer a fully contained setup? Open the folder in VS Code and choose
> **Reopen in Container**. The dev container installs everything for you.

---

## The dataset

An e-government **Unified Services Portal**: citizens raise service
requests (water fault, waste collection, permits, licences) through several
channels, and directorates resolve them against a service-level target.

| Object | Grain | Used for |
|--------|-------|----------|
| `raw.service_requests` | one row per request (messy) | Day 1 cleaning, EDA |
| `raw.services` | one row per service | dimension, SLA target |
| `raw.channels` | one row per channel | dimension |
| `raw.districts` | one row per district | dimension |
| `raw.departments` | one row per directorate | dimension |

Modelling targets introduced later in the week: `sla_met` (classification,
was the request resolved within its target) and `resolution_hours`
(regression, how long it took).

---

## Repository layout

```
ADS-DBT_Course/
  data/            dataset generator, raw CSVs, clean seeds
  notebooks/       teaching notebooks, one folder per day
  labs/            exercises (with a solutions/ folder per day)
  dbt/             dbt project (Days 4 to 5)
  sql/             helper SQL
  docker-compose.yml   Postgres + Adminer
  seed_postgres.py     loads the dataset into Postgres
  requirements.txt
```

---

## Daily map

1. **Foundations with Python** - Python for analysis, notebooks, NumPy, Pandas, cleaning, EDA
2. **Visualisation & analytical techniques** - Matplotlib, Seaborn, feature engineering, framing
3. **Machine learning with Python** - regression, classification, evaluation
4. **Transformation & modelling with dbt** - analytics engineering on Postgres
5. **Pipelines & end-to-end analytics** - orchestration (Airflow and Dagster), capstone
