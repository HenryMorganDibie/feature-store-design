# Data Flow Diagrams

## Overall Architecture

\\\
+-----------------------------------------------------------------+
¦                    SHARED — Both Approaches                      ¦
¦                                                                  ¦
¦  [Source Systems]  ?  Airbyte (3x daily)  ?  l0 Redshift        ¦
¦                                                  ¦               ¦
¦                                           Airflow + dbt          ¦
¦                                                  ¦               ¦
¦                                           l1 Silver              ¦
¦                              (fact_orders, dim_shoppers, ...)    ¦
+-----------------------------------------------------------------+
                               ¦
              +----------------------------------+
              ¦                                  ¦
   +----------?----------+            +----------?----------+
   ¦   APPROACH A        ¦            ¦   APPROACH B        ¦
   ¦   dbt-Native        ¦            ¦   Feast (OSS)       ¦
   ¦                     ¦            ¦                     ¦
   ¦  l3 Feature tables  ¦            ¦  S3 sources export  ¦
   ¦  (Redshift + S3)    ¦            ¦  feast materialize  ¦
   ¦                     ¦            ¦  Feast offline store¦
   +---------------------+            +---------------------+
              ¦                                  ¦
              +----------------------------------+
                               ¦
                    FeatureClient (Python)
                    Identical DS-facing API
                               ¦
                    +---------------------+
                    ¦   Amazon SageMaker  ¦
                    ¦  Notebooks/Training ¦
                    ¦  Batch Transform    ¦
                    +---------------------+
\\\

## Point-in-Time Correctness

\\\
APPROACH A: dbt-Native (Manual)
---------------------------------------------------------
Time:   Jan 2023      Jul 2023      Jan 2024      Today
          ¦               ¦             ¦            ¦
          ¦         Order placed        ¦            ¦
          ¦         Jul 2023 ----------?¦            ¦
          ¦                             ¦            ¦
          ¦    Daily Snapshots (S3)     ¦            ¦
          ¦    ¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦    ¦            ¦
          ¦                             ¦            ¦
          ¦    PIT join SQL:            ¦            ¦
          ¦    AND s.snapshot_date      ¦            ¦
          ¦      = DATE(order.created)  ¦            ¦
          ¦                             ¦            ¦
          ¦    ??  If this condition    ¦            ¦
          ¦    is omitted ? LEAKAGE     ¦            ¦
          ¦    (today's values used     ¦            ¦
          ¦     for historical event)   ¦            ¦

APPROACH B: Feast (Native)
---------------------------------------------------------
Time:   Jan 2023      Jul 2023      Jan 2024      Today
          ¦               ¦             ¦            ¦
          ¦         Order placed        ¦            ¦
          ¦         Jul 2023            ¦            ¦
          ¦                             ¦            ¦
          ¦    entity_df:               ¦            ¦
          ¦    entity_id = order-A      ¦            ¦
          ¦    event_timestamp = Jul 23 ¦            ¦
          ¦                ¦            ¦            ¦
          ¦                ?            ¦            ¦
          ¦    get_historical_features()¦            ¦
          ¦    ? returns Jul 2023 values¦            ¦
          ¦    structurally enforced ? ¦            ¦
\\\

## S3 Layout

\\\
APPROACH A: dbt-Native
s3://[client]-feature-store/
  features/
    shopper/
      snapshot_date=2026-04-01/part-00000.parquet
      snapshot_date=2026-04-02/part-00000.parquet
    order/
      snapshot_date=2026-04-01/part-00000.parquet
    merchant/
      snapshot_date=2026-04-01/part-00000.parquet
    training_sets/
      fraud/snapshot_date=2026-04-01/part-00000.parquet
      credit_risk/snapshot_date=2026-04-01/part-00000.parquet
      debt_collection/snapshot_date=2026-04-01/part-00000.parquet
  registry/
    feature_metadata.json
  audit/quality_reports/

APPROACH B: Feast
s3://[client]-feature-store/
  feast/
    registry/registry.db
    offline/
      shopper/year=2026/month=04/day=01/part-00000.parquet
      order/year=2026/month=04/day=01/part-00000.parquet
      merchant/year=2026/month=04/day=01/part-00000.parquet
    sources/
      shopper/event_timestamp=2026-04-01/part-00000.parquet
      order/event_timestamp=2026-04-01/part-00000.parquet
      merchant/event_timestamp=2026-04-01/part-00000.parquet
\\\
"@

New-File "02_architecture/.gitkeep" ""

# ============================================================
# 03 TECHNICAL SPECIFICATIONS
# ============================================================
Write-Host "[4/7] 03_technical_specifications..." -ForegroundColor Yellow

New-File "03_technical_specifications/README.md" @"
# Deliverable 03 — Technical Specifications

**Effort:** ~4–5 hrs

---

## Contents

| File / Folder | What It Covers |
|---|---|
| [specifications.md](./specifications.md) | dbt model patterns, S3 conventions, snapshot strategy, metadata schema, VIEW vs TABLE guidance |
| [code_patterns/dbt_models/](./code_patterns/dbt_models/) | Entity feature SQL for shopper, order, merchant + .yml catalog/test files |
| [code_patterns/feature_client/](./code_patterns/feature_client/) | FeatureClient: dbt-native backend (awswrangler) and Feast backend |
| [code_patterns/sagemaker/](./code_patterns/sagemaker/) | SageMaker notebook, training job, and batch transform integration patterns |
| [code_patterns/airflow_dags/](./code_patterns/airflow_dags/) | Feature pipeline DAGs for both approaches |
