# Technical Specifications

---

## 1. Entity Model

Three entities drive the entire feature store. All feature tables follow this model.

| Entity | Primary Key | Refresh | Used By |
|---|---|---|---|
| shopper | uuid | Daily | Fraud, Credit Risk, Debt Collection |
| order | order_id | Daily | Fraud, Credit Risk |
| merchant | merchant_id | Daily | Fraud, Credit Risk, Debt Collection |

---

## 2. dbt Layer Conventions

| Layer | Name | Purpose | Feature Store Role |
|---|---|---|---|
| l0 | Bronze | Raw Airbyte replicas | Source only — never queried directly in feature models |
| l1 | Silver | Cleaned entities via dbt | Foundation for all feature computation |
| l2 | Gold | KPIs and dashboard tables | Not consumed by feature store |
| l3 | Feature | Entity feature tables | New layer added by this project |

---

## 3. VIEW vs TABLE Materialization

| Feature Type | Materialization | Examples | Rationale |
|---|---|---|---|
| Simple selects from l1 | VIEW | shopper_age, shopper_province, order_value | Zero storage cost. Always current. |
| Multi-table joins from l1 | VIEW | Order enriched with merchant sector | Redshift handles at query time efficiently. |
| Window aggregations | TABLE | shopper_n_orders_30d, merchant_fraud_rate_60d | Too expensive to recompute at query time. |
| PIT snapshots | TABLE on S3 Parquet | All features as of a specific date | Core requirement for PIT correctness. |
| Bureau features | TABLE | bureau_score, unpaid_balance | External data; snapshot rather than re-query live. |

**Edge case:** Never use VIEWs for any feature involving a subquery on a table larger than
10M rows. Even simple logic causes a full table scan on every SageMaker notebook query.
Materialise as TABLE and refresh daily via Airflow.

---

## 4. S3 Parquet Schema Conventions

| Column | dbt-Native | Feast |
|---|---|---|
| Primary key | entity_id VARCHAR — consistent across all entity feature tables | entity_id VARCHAR — must match Feast Entity join_key exactly |
| Timestamp | snapshot_date DATE — partition key for PIT joins | event_timestamp TIMESTAMP — required by Feast; drives all PIT joins |
| Version | feature_version VARCHAR (v1, v2) — manual column in every record | Managed by FeatureView name versioning (shopper_features_v2) |
| Naming | category_featurename (e.g., shopper_n_orders_30d) | Same naming convention recommended for consistency |

---

## 5. Feature Naming Convention

\\\
{entity}_{category}_{description}_{window}

Examples:
  shopper_n_orders_30d          ? shopper entity, count feature, 30-day window
  shopper_total_spend_lifetime  ? shopper entity, sum feature, lifetime window
  merchant_fraud_rate_60d       ? merchant entity, rate feature, 60-day window
  order_temporal_hour_sin       ? order entity, temporal category, cyclical encoding
  shopper_bureau_score          ? shopper entity, bureau category
\\\

---

## 6. Feature Versioning Strategy

| Scenario | Action | Notes |
|---|---|---|
| Adding a new feature column | Add to existing model — no version bump | Safe: additive change, no downstream breakage |
| Changing feature calculation logic | Create v2 model, run in parallel for 2 weeks, deprecate v1 | Never update in place — silently breaks downstream consumers |
| Renaming a feature | Add alias in v2, deprecate old name after migration window | Coordinate with DS team before deprecating |
| Removing a feature | Set to NULL in current model, remove after confirmed zero usage | Query feature registry to verify zero usage before removing |

---

## 7. Metadata Registry Schema

\\\sql
CREATE TABLE feature_store.feature_registry (
    feature_id          VARCHAR(100)  NOT NULL,
    entity              VARCHAR(50)   NOT NULL,
    feature_version     VARCHAR(10)   NOT NULL,
    description         VARCHAR(500),
    domains             VARCHAR(200),   -- comma-separated: fraud,credit_risk,debt_collection
    owner               VARCHAR(100),
    is_pii              BOOLEAN       DEFAULT FALSE,
    gdpr_category       VARCHAR(100),  -- personal_data, financial_personal_data, etc.
    access_role         VARCHAR(100),  -- ds_standard, ds_privileged
    is_deprecated       BOOLEAN       DEFAULT FALSE,
    deprecated_date     DATE,
    successor_feature   VARCHAR(100),
    created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (feature_id, feature_version)
);
\\\

---

## 8. Retention and Storage Cost

| Retention | Cost at S3 Standard | Notes |
|---|---|---|
| 90 days | ~\.66/month | Minimum. Covers most retraining cycles. |
| 365 days | ~\.72/month | Recommended: GDPR audit + multi-year model reproducibility. |
| After 365 days | ~\.004/GB/month (Glacier) | S3 Lifecycle rule to Glacier. Automated via AWS. |

**Recommendation:** 365-day retention at S3 Standard for both approaches.
S3 Lifecycle rule to Glacier after 365 days. Storage cost is identical
regardless of which approach is chosen.

---

## 9. Backfill Strategy

When a feature definition changes, historical values must be recomputed.

### dbt-Native Backfill

\\\ash
# Step 1: Update the feature logic in the dbt model
# Step 2: Backfill the Redshift feature table across the full date range
dbt run --models fct_features_shopper \
  --vars '{"start_date": "2023-01-01", "end_date": "2026-04-15"}'

# Step 3: Re-export the backfilled table to S3 Parquet
python export_to_s3.py --entity shopper --start 2023-01-01 --end 2026-04-15

# Step 4: Bump feature_version to v2
# Estimated total time: 2–4 hours DE time
\\\

### Feast Backfill

\\\ash
# Steps 1–3: Same as dbt-native (rebuild l1, re-export to S3 sources)
# Step 4: Re-materialise Feast offline store across the full date range
feast materialize 2023-01-01T00:00:00 2026-04-15T00:00:00
# Estimated total time: 4–8 hours DE time (extra S3 file generation step)
\\\

| Dimension | dbt-Native | Feast |
|---|---|---|
| Steps | 3 | 4–5 |
| Estimated DE time | 2–4 hours | 4–8 hours |
| Risk of corruption | Low (dbt transactions atomic per model) | Low (feast materialize is idempotent) |
