# Open Questions — All 10 Answered

Direct answers to all 10 questions from the project brief.

---

## Q1. Tool Selection

**Given the stack, team size, batch-only requirements, and data scale — dbt-native, Feast, or SageMaker Feature Store?**

**Recommendation: dbt-native now, Feast when the online store is required.**

See [01_build_vs_buy](../01_build_vs_buy/) for the full scored evaluation.
The short version: dbt-native scores 4.1/5 vs Feast 3.3/5 and SageMaker FS 3.6/5 against
the client's specific binding constraints. The gap closes and reverses if the online store
timeline is within 12–18 months.

---

## Q2. Point-in-Time Correctness

**How to handle features like "shopper's order count at the time of this specific order" without data leakage?**

### The Problem

Features like \shopper_n_orders_30d\ change every day. A fraud model trained on an order
from 14 months ago must use feature values as they existed on that order date — not today's
values. Using today's values is silent data leakage that inflates training metrics and
causes production failures.

### dbt-Native: Manual Snapshot Strategy

\\\sql
-- Daily dbt snapshot captures full feature state each day
{{ config(strategy='timestamp', updated_at='created_at') }}
SELECT * FROM {{ ref('fct_features_shopper') }}

-- Training set SQL: snapshot_date join is mandatory every time
LEFT JOIN feature_snapshots.fct_features_shopper_snapshot s
  ON fo.shopper_uuid = s.entity_id
  AND s.snapshot_date = DATE(fo.created_at)  -- PIT: must never be omitted
\\\

**Risk:** A DE engineer writing SQL directly against Redshift outside FeatureClient
can omit the snapshot_date condition. FeatureClient enforces it at the API level —
making this risk low once adoption is complete.

### Feast: Native PIT Correctness

\\\python
entity_df = pd.DataFrame({
    'entity_id':       ['order-A', 'order-B'],
    'event_timestamp': ['2023-07-15', '2023-11-03'],
})
# Feast returns features as of 2023-07-15 for order-A
# structurally enforced — no way to accidentally retrieve today's values
result = store.get_historical_features(entity_df=entity_df, features=[...]).to_df()
\\\

**Verdict:** Both approaches have equivalent PIT safety at the DS consumption layer
when FeatureClient is used. The residual risk for dbt-native is a bypass of FeatureClient —
detectable via Airflow logs and S3 access patterns.

---

## Q3. Time Travel / Reproducibility

**Best approach for "give me features as they looked on date X"?**

### dbt-Native

\\\python
# FeatureClient: pass as_of_date to read the correct S3 partition
features = client.get_features(
    entity='shopper',
    entity_ids=['uuid-001'],
    as_of_date=date(2023, 7, 15),  # any historical date within 365-day retention
)
\\\

Reads the S3 Parquet partition for \snapshot_date=2023-07-15\ via awswrangler.
Retention recommendation: 365 days at S3 Standard (~\.72/month), then Glacier.

### Feast

\\\python
# Pass any historical date as event_timestamp — Feast handles it automatically
audit_df = pd.DataFrame({
    'entity_id': ['shopper-uuid-123'],
    'event_timestamp': ['2023-07-15'],
})
historical = store.get_historical_features(audit_df, features=[...]).to_df()
\\\

**Verdict:** Both work equally well for GDPR audit and model reproducibility.
S3 retention policy is identical for both approaches.

---

## Q4. Feature Versioning

**When a feature calculation changes — create v2 or update in place?**

**Never update in place.** Always create a new version.

| Scenario | Action |
|---|---|
| Adding a new column | Add to existing model — no version bump needed |
| Changing calculation logic | Create v2 model, run v1 and v2 in parallel for 2 weeks, deprecate v1 |
| Renaming a feature | Add alias in v2, deprecate old name after migration window |
| Removing a feature | Set to NULL in current model, remove after confirmed zero usage |

\\\sql
-- v2 model: runs in parallel with v1 for 2-week migration window
-- models/features/shopper/fct_features_shopper_v2.sql
{{ config(materialized='table', tags=['feature_store', 'shopper']) }}
SELECT
  ...,
  -- Fixed: n_orders_30d now excludes cancelled orders
  COUNT(CASE WHEN o.created_at >= DATEADD(day,-30,CURRENT_DATE)
              AND o.status != 'cancelled' THEN 1 END) AS shopper_n_orders_30d,
  ...
\\\

\\\python
# DS pins to a specific version via FeatureClient
features = client.get_features(entity='shopper', entity_ids=[...], feature_version='v1')
\\\

---

## Q5. Materialization Strategy

**Validate the VIEW vs TABLE approach. Edge cases?**

Validated. See [03_technical_specifications/specifications.md](../03_technical_specifications/specifications.md)
Section 3 for the full table.

**Key edge cases:**
- Never use VIEWs for any feature involving a subquery on a table larger than 10M rows —
  full table scan on every SageMaker notebook query
- Bureau features (Equifax): always TABLE — external data must be snapshotted, not re-queried live
- Behavioral event aggregations (Mixpanel, 29M events/month): always TABLE — volume makes VIEW impractical

---

## Q6. Schema Evolution

**How to handle adding/removing/changing features without breaking downstream models?**

| Change Type | Safe? | Action |
|---|---|---|
| Adding a new column | ? Yes | Add to model, update .yml, update registry. No consumer impact. |
| Changing calculation logic | ?? Breaking | Create v2 model. 2-week parallel run. Notify DS via Slack. Deprecate v1 after migration window. |
| Renaming a column | ?? Breaking | Add new column name in v2, keep old name as alias during migration. |
| Removing a column | ?? Breaking | Set to NULL first. Query registry to confirm zero usage. Remove after 2-week window. |
| Changing data type | ?? Breaking | Always a v2 — type changes break downstream consumers silently in some cases. |

**Governance rule:** Any breaking change requires a PR, a 2-week migration window, and
a Slack notification to #feature-store with the deprecation timeline.

---

## Q7. Data Quality and Testing

**What tests and monitoring should be in place per feature table?**

### dbt Test Layer (runs before every S3 export)

| Test | Applied To | What It Catches |
|---|---|---|
| not_null | entity_id, snapshot_date, feature_version | Missing primary keys — breaks all FeatureClient joins |
| unique | entity_id per snapshot_date | Duplicate rows — causes double-counting in training sets |
| accepted_range | shopper_age (18–120), rate features (0.0–1.0), n_orders (>=0) | Outliers and source data errors |
| relationships | entity_id must exist in dim_shoppers / fact_orders / dim_merchants | Orphaned feature rows for deleted entities |
| source freshness | All l0 Airbyte sources | Detects Airbyte sync failures before they propagate |

### Airflow DAG Failure Policy

\\\
run_dbt_tests ? [FAIL] ? block S3 export + Slack alert to #feature-store
              ? [PASS] ? export_to_s3 proceeds
\\\

### Drift Detection

Once features are centralised, the existing drift detection system can be updated to read
from one consistent source:
- Store baseline statistics at model training time: mean, std, p5, p95 per feature
- Daily Airflow task compares current distributions against baselines
- Alert on drift beyond 3 standard deviations

---

## Q8. PII Handling and GDPR

**Access control strategy for features containing sensitive data?**

All enforcement is at the Redshift layer — approach-agnostic (identical for dbt-native and Feast).

| Feature Category | GDPR Classification | Access Role |
|---|---|---|
| Shopper age, province, country | Personal data (Art. 4) | ds_standard_role |
| Delivery address, postal code | Personal data (Art. 4) | ds_standard_role (aggregated only; raw address not stored as a feature) |
| Bureau score, unpaid balance | Financial personal data (Art. 4) | ds_privileged_role only |
| Device identifiers, IP-derived location | Personal data if linkable (Art. 4) | ds_standard_role (aggregated signals only) |

\\\sql
-- Column-level access control: identical for both approaches
GRANT SELECT ON feature_store.fct_features_shopper TO ds_standard_role;
REVOKE SELECT (bureau_score, unpaid_balance, operations_count)
    ON feature_store.fct_features_shopper FROM ds_standard_role;
GRANT SELECT (bureau_score, unpaid_balance, operations_count)
    ON feature_store.fct_features_shopper TO ds_privileged_role;
-- Enable Redshift audit logging for all privileged column access
\\\

PII features are tagged in the .yml catalog (\meta: pii: true, gdpr_category: ...\)
and in the Redshift feature_registry table for programmatic access.

---

## Q9. DS Workflow Integration

**How should DS consume features in SageMaker notebooks — SQL directly or Python wrapper?**

**Python wrapper via FeatureClient. DS never writes SQL against feature tables directly.**

\\\python
from feature_client import FeatureClient
from datetime import date

client = FeatureClient()

# Get a training set — PIT correctness handled internally
df = client.get_training_set(domain='fraud', start_date=date(2023,5,1), end_date=date(2024,5,31))

# Get features for specific entities
features = client.get_features(entity='shopper', entity_ids=['uuid-1','uuid-2'], as_of_date=date.today())

# Browse the catalog before building new features
catalog = client.list_features(entity='shopper')
\\\

This is the same two-line API regardless of whether the backend is dbt-native or Feast.
When the migration happens, zero DS notebooks change.

See [03_technical_specifications/code_patterns/sagemaker/](../03_technical_specifications/code_patterns/sagemaker/)
for full notebook, training job, and batch transform patterns.

---

## Q10. Governance Model

**Who owns feature definitions? PR review process? Deprecation policy?**

| Decision | Owner | Process |
|---|---|---|
| New feature | DS proposes, DE owns | DS opens PR to models/features/. DE reviews SQL logic, naming convention, and dbt tests. Merged after DE approval. |
| Logic change | DE owns | Create v2 model. 2-week parallel run. Slack notification to #feature-store. Deprecate v1 after migration window. |
| PII classification | DE + Legal | Legal review required before PR merge. Tag in .yml and registry table. |
| Deprecation | DE owns | Set is_deprecated=true in registry. Confirm zero usage. NULL the column. Remove after 2 weeks. |

**Naming convention enforced at PR review:**

\\\
{entity}_{category}_{description}_{window}
? shopper_n_orders_30d
? merchant_fraud_rate_60d
? fraud_rate         ? missing entity prefix
? shopper_orders     ? missing category and window
\\\

**Adoption enforcement:** Track FeatureClient calls in Airflow logs.
After launch, any new ad-hoc S3 feature save by a DS engineer is flagged in
the weekly DE review. The target is zero ad-hoc saves within 3 months.
