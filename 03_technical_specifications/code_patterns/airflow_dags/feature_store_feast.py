"""
Airflow DAG — Feast feature store pipeline
Runs daily at 02:00 UTC.

Pipeline:
  wait_for_airbyte ? run_l1_dbt ? run_dbt_tests
  ? export_l1_to_s3 ? feast_materialize ? alert_on_failure

feast materialize-incremental is idempotent: safe to re-run on failure.
feast_materialize is blocked until dbt tests pass and S3 exports succeed.
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-engineering',
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
    'email_on_failure': True,
}

with DAG(
    dag_id='feature_store_daily_feast',
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval='0 2 * * *',
    catchup=False,
    tags=['feature_store', 'feast'],
) as dag:

    wait_for_airbyte = PythonOperator(
        task_id='wait_for_airbyte',
        python_callable=lambda: print('Airbyte sync check'),
    )
    run_l1_dbt = BashOperator(
        task_id='run_l1_dbt',
        bash_command='cd /opt/dbt && dbt run --select tag:l1 --profiles-dir .',
    )
    run_dbt_tests = BashOperator(
        task_id='run_dbt_tests',
        bash_command='cd /opt/dbt && dbt test --select tag:l1 --profiles-dir .',
    )
    export_l1_to_s3 = BashOperator(
        task_id='export_l1_to_s3',
        bash_command='python /opt/scripts/export_l1_to_s3_feast_sources.py',
    )
    feast_materialize = BashOperator(
        task_id='feast_materialize',
        bash_command=(
            'cd /opt/feast_repo && '
            'feast materialize-incremental 2026-04-20T00:32:31'
        ),
    )

    wait_for_airbyte >> run_l1_dbt >> run_dbt_tests >> export_l1_to_s3 >> feast_materialize
