# Deliverable 02 — Architecture Document

**Effort:** ~5–6 hrs  
**Full document:** See \FeatureStore_Architecture_dbtNative_vs_Feast_PUBLIC.docx\ in this folder

---

## Overview

This document presents two parallel feature store architectures — dbt-native and Feast —
covering storage, computation, SageMaker serving, catalog, monitoring, and point-in-time
correctness. Neither approach is pre-selected; the goal is an honest engineering comparison.

---

## Shared Foundation (Both Approaches)

Both architectures share the same ingestion pipeline and l0/l1 transformation layer.
The divergence point is what happens after l1.

\\\
Source Systems (Transactional, Bureau, CDP)
        |
        v  Airbyte (3x daily)
l0 (Bronze)   Raw replicas in Redshift
        |
        v  Airflow + dbt
l1 (Silver)   fact_orders, dim_shoppers, dim_merchants, dim_bureau
        |
   [diverges here]
   /              \
Approach A        Approach B
dbt-Native        Feast
\\\

---

## Approach A: dbt-Native Data Flow

\\\
l1 (Silver)
   |
   v  Airflow + dbt (after l1)
l3 (Feature)   fct_features_shopper, fct_features_order, fct_features_merchant
   |                          |
   v                          v
Redshift query layer    S3 Parquet Snapshots
via Redshift Spectrum   partitioned by entity + snapshot_date
   +------------------------------+
                  |
                  v  FeatureClient (awswrangler reads S3)
      SageMaker Notebooks / Batch Transform Jobs
\\\

---

## Approach B: Feast Data Flow

\\\
l1 (Silver)
   |
   v  Airflow: export l1 entity tables to S3 Parquet (new step)
S3 Feature Sources   shopper/, order/, merchant/ (partitioned by event_timestamp)
   |
   v  Airflow: feast materialize (daily, after dbt tests pass)
Feast Offline Store (S3) + Feast Registry (S3)
   |
   v  FeatureClient wraps Feast Python SDK
      SageMaker Notebooks / Batch Transform Jobs
      [Future: feast materialize-incremental ? Redis ? real-time scoring endpoint]
\\\

---

## SageMaker Integration

Both approaches integrate with SageMaker via the FeatureClient abstraction layer.
See [../03_technical_specifications/code_patterns/sagemaker/](../03_technical_specifications/code_patterns/sagemaker/)
for notebook, training job, and batch transform patterns.

\\\python
from feature_client import FeatureClient
from datetime import date

client = FeatureClient()  # connects to dbt-native OR Feast transparently

# In a SageMaker notebook or training script
df = client.get_training_set(
    domain='fraud',
    start_date=date(2023, 5, 1),
    end_date=date(2024, 5, 31),
)
\\\

---

## Engineering Effort Comparison

| Task | dbt-Native (Days) | Feast (Days) |
|---|---|---|
| Infrastructure setup | 2–3 | 3–4 |
| Entity feature models (shopper, order, merchant) | 5–6 | 4–5 |
| PIT correctness implementation | 3–4 | 1–2 |
| FeatureClient integration | 3–4 | 3–4 |
| Training set composition (3 domains) | 3–4 | 2–3 |
| Feature catalog and registry | 3–4 | 1–2 |
| GDPR and PII access controls | 2–3 | 2–3 |
| Data quality tests and Airflow alerting | 2–3 | 2–3 |
| DS and DE onboarding | 2–3 | 3–4 |
| **Total** | **25–34 days** | **21–30 days** |

---

## Monthly Infrastructure Cost

| Phase | dbt-Native | Feast |
|---|---|---|
| Batch-only (SQLite registry) | ~\–13/month | ~\–13/month |
| Batch-only (PostgreSQL registry) | N/A | ~\–63/month |
| With online store (ElastiCache Redis) | N/A — migration required | ~\–273/month |

---

## Diagrams

See [diagrams/](./diagrams/) for:
- Overall architecture (shared l0/l1 ? dbt-native vs Feast serving paths)
- Point-in-time correctness (manual snapshot vs native Feast enforcement)
- Phased implementation timelines
