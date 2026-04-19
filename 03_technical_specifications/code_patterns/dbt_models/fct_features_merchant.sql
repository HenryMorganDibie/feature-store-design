-- Entity: merchant (merchant_id)
-- Refresh: daily at 02:00 UTC via Airflow
-- Version: v1
-- Used by: Fraud, Credit Risk, Debt Collection

{{ config(
    materialized='table',
    dist='merchant_id',
    sort='snapshot_date',
    tags=['feature_store', 'merchant', 'daily']
) }}

SELECT
    m.merchant_id                                                             AS entity_id,
    CURRENT_DATE                                                              AS snapshot_date,
    'v1'                                                                      AS feature_version,
    CURRENT_TIMESTAMP                                                         AS created_at,
    -- Profile features
    m.sector                                                                  AS merchant_sector,
    m.subsector                                                               AS merchant_subsector,
    m.platform                                                                AS merchant_platform,
    DATEDIFF(month, m.onboarding_date, CURRENT_DATE)                         AS merchant_months_active,
    -- Risk features (60-day rolling window)
    COUNT(CASE WHEN o.created_at >= DATEADD(day,-60,CURRENT_DATE)
               AND o.is_fraud = 1 THEN 1 END) * 1.0
    / NULLIF(COUNT(CASE WHEN o.created_at >= DATEADD(day,-60,CURRENT_DATE)
                        THEN 1 END), 0)                                      AS merchant_fraud_rate_60d,
    COUNT(CASE WHEN o.created_at >= DATEADD(day,-60,CURRENT_DATE)
               AND o.is_rejected = 1 THEN 1 END) * 1.0
    / NULLIF(COUNT(CASE WHEN o.created_at >= DATEADD(day,-60,CURRENT_DATE)
                        THEN 1 END), 0)                                      AS merchant_rejection_rate_60d,
    m.risk_category                                                           AS merchant_risk_category
FROM {{ ref('dim_merchants') }} m
LEFT JOIN {{ ref('fact_orders') }} o ON m.merchant_id = o.merchant_id
GROUP BY
    m.merchant_id, m.sector, m.subsector, m.platform,
    m.onboarding_date, m.risk_category
