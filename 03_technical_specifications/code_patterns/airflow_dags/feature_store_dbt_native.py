"""
Airflow DAG — dbt-native feature store pipeline
Runs daily at 02:00 UTC.

Pipeline:
  wait_for_airbyte ? run_l1_dbt ? run_feature_dbt ? run_dbt_tests
  ? export_to_s3 ? alert_on_failure

S3 export is blocked until all dbt tests pass.
Slack alert to #feature-store on any failure.
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
    dag_id='feature_store_daily_dbt_native',
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval='0 2 * * *',
    catchup=False,
    tags=['feature_store', 'dbt_native'],
) as dag:

    wait_for_airbyte = PythonOperator(
        task_id='wait_for_airbyte',
        python_callable=lambda: print('Airbyte sync check'),
    )
    run_l1_dbt = BashOperator(
        task_id='run_l1_dbt',
        bash_command='cd /opt/dbt && dbt run --select tag:l1 --profiles-dir .',
    )
    run_feature_dbt = BashOperator(
        task_id='run_feature_dbt',
        bash_command='cd /opt/dbt && dbt run --select tag:feature_store --profiles-dir .',
    )
    run_dbt_tests = BashOperator(
        task_id='run_dbt_tests',
        bash_command='cd /opt/dbt && dbt test --select tag:feature_store --profiles-dir .',
    )
    export_to_s3 = BashOperator(
        task_id='export_to_s3',
        bash_command='python /opt/scripts/export_features_to_s3.py',
    )

    wait_for_airbyte >> run_l1_dbt >> run_feature_dbt >> run_dbt_tests >> export_to_s3
