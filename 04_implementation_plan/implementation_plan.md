# Implementation Plan

**Effort:** ~2–3 hrs design  
**Principle:** Features first, catalog later. Ship 3–5 high-value shared features fast,
prove adoption, then formalise governance. No big-bang rollout.

---

## Approach A: dbt-Native — 10 Weeks

| Week | Milestone | Key Tasks |
|---|---|---|
| 1 | Infrastructure setup | Create models/features/ directory. Add feature_store schema to Redshift. Create S3 bucket and prefix structure. Set up IAM roles (ds_standard_role, ds_privileged_role). Create feature_store.feature_registry table. |
| 2 | First 5 shared shopper features | Implement fct_features_shopper with: shopper_n_orders_30d, shopper_total_spend_30d, shopper_days_since_last_order, shopper_tenure_days, shopper_avg_order_value. Add dbt tests. Run first manual S3 snapshot export. |
| 3 | FeatureClient v1 | Implement get_features() for shopper entity via awswrangler. Internal DE testing. Share with 1–2 DS for pilot. Collect feedback. |
| 4 | Order and merchant feature tables | Implement fct_features_order and fct_features_merchant. Add dbt tests for both. Add to Airflow DAG. |
| 5 | PIT snapshots and Airflow export | Implement dbt snapshot models for all three entities. Implement daily S3 Parquet export in Airflow. Block S3 export on dbt test failure. |
| 6 | Training sets: fraud and credit risk | Implement fraud_training_set.sql and credit_risk_training_set.sql with explicit PIT joins. Implement get_training_set() in FeatureClient. |
| 7 | Bureau features and GDPR controls | Integrate bureau features into fct_features_shopper. Apply Redshift column-level grants for ds_privileged_role. Enable audit logging. Tag PII in registry. |
| 8 | Feature catalog | Enable dbt docs. Populate feature_registry table for all shipped features. Add list_features() to FeatureClient. |
| 9 | Drift detection and monitoring | Implement feature_baselines table. Wire drift detection SQL to feature tables. Configure Slack alerting in Airflow. |
| 10 | Full adoption + debt collection | Implement debt_collection_training_set.sql. Run DS onboarding workshop. Target 100% DS adoption of FeatureClient for all new model training. |

**Phase breakdown:**
- Phase 1 (Weeks 1–3): Foundation — infrastructure, first 5 features, FeatureClient v1
- Phase 2 (Weeks 4–8): Core coverage — all entities, training sets, GDPR, catalog
- Phase 3 (Weeks 9–10): Adoption — monitoring, debt collection, onboarding

---

## Approach B: Feast — 16–18 Weeks (Part-Time DE)

> Timeline note: The 12-week schedule below assumes a dedicated DE.
> With a 1–2 person DE team working part-time, realistic calendar time is 16–18 weeks.

| Week | Milestone | Key Tasks |
|---|---|---|
| 1–2 | Feast foundation | Set up feast_repo. Configure feature_store.yaml (AWS provider, S3 registry, S3 offline store). Define Entity objects (shopper, order, merchant). Set up Airflow task for feast apply on PR merge. Test feast materialize in staging. |
| 3 | First 5 shared shopper features | Define shopper_features FeatureView with 5 shopper features. Run first feast materialize. Validate output via get_historical_features(). Confirm PIT correctness. |
| 4 | FeatureClient (Feast backend) | Implement FeatureClient wrapping Feast SDK with identical external API. Internal DE testing. Share with 1–2 DS for pilot. |
| 5 | Order and merchant FeatureViews | Define order_features and merchant_features FeatureViews. Implement S3 exports for all three entities. Add to Airflow DAG. |
| 6 | Training sets: fraud and credit risk | Implement get_training_set() using get_historical_features(). Validate PIT correctness against known historical feature values. |
| 7 | Bureau features and GDPR controls | Add bureau features to shopper_features FeatureView with PII tags. Apply Redshift column-level grants. feast apply to update registry. |
| 8 | Feature catalog and DS onboarding | Enable list_features() via Feast SDK. Run DS onboarding workshop: Feast concepts, entity_df pattern, FeatureClient API. |
| 9 | Drift detection and monitoring | Implement feature_baselines table. Wire drift detection to Feast offline store output. Configure Slack alerting. |
| 10 | Debt collection domain | Add debt_collection to domain features. Implement get_training_set() for debt collection. DS team validates output. |
| 11–12 | Hardening and documentation | Load test feast materialize with full dataset volumes. Finalise FeatureClient documentation. Validate registry S3 backup and recovery. Target 100% DS adoption. |

---

## Success Metrics (Both Approaches)

| Metric | Target | How to Measure |
|---|---|---|
| DS team adoption | 100% using shared features within 3 months of launch | Track FeatureClient calls in Airflow logs. Zero new ad-hoc S3 feature saves after launch. |
| Feature engineering time per model | Reduced from ~20 hours to ~2 hours | DS team self-report at onboarding workshop. Track via notebook timestamps. |
| Feature reuse across domains | >50% of features used by 2 or more domains | Query feature registry: count distinct domains per feature. |
| Time to new training set | Less than 1 day (currently ~1 week) | Measure from DS request to first model training run using feature store data. |
| PIT correctness | Zero leakage incidents confirmed on model validation | Compare held-out future data performance vs historical baseline per domain. |

---

## Feast Migration Trigger Conditions

If starting with dbt-native, migrate to Feast when **any** of these are confirmed:

| Trigger | What It Means |
|---|---|
| Online store requirement confirmed with a delivery date | Primary trigger. Initiate migration immediately — do not wait for the deadline. |
| Feature definition changes more than once per month | Feast backfill overhead accumulates faster than dbt-native. dbt-native's simpler backfill becomes a meaningful advantage. |
| DE team grows to 3+ engineers | More engineers means more concurrent feast apply risk and more benefit from Feast's code-driven registry. |
