-- Airflow keeps its own metadata (DAG runs, task states, connections) in a
-- database of its own. It must not share ads_dbt_analytics, because the
-- warehouse is dropped and rebuilt constantly and the scheduler's history
-- should survive that.
SELECT 'CREATE DATABASE airflow OWNER ads_dbt'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec
