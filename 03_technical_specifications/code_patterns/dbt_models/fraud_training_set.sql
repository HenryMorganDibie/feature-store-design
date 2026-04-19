-- Fraud training set
-- PIT correctness: snapshot_date join is MANDATORY on every feature table join
-- Omitting the snapshot_date condition silently uses today's feature values
-- for historical orders — this is data leakage that inflates training metrics

{{ config(
    materialized='table',
    schema='feature_store',
    tags=['training_set', 'fraud']
) }}

SELECT
    o.entity_id                         AS order_id,
    o.snapshot_date,
    -- Order features
    o.order_value,
    o.order_n_instalments,
    o.cart_num_items,
    o.cart_has_discount,
    o.device_platform,
    o.geo_distance_km,
    o.temporal_hour_sin,
    o.temporal_hour_cos,
    o.temporal_day_of_week,
    -- Shopper features (PIT: as of order date)
    s.shopper_age,
    s.shopper_tenure_days,
    s.shopper_n_orders_30d,
    s.shopper_total_spend_30d,
    s.shopper_avg_order_value,
    s.shopper_days_since_last_order,
    -- Merchant features (PIT: as of order date)
    m.merchant_sector,
    m.merchant_fraud_rate_60d,
    m.merchant_rejection_rate_60d,
    m.merchant_risk_category,
    -- Label
    fo.is_fraud                         AS label
FROM {{ ref('fct_features_order') }} o
JOIN {{ ref('fact_orders') }} fo
    ON o.entity_id = fo.order_id
LEFT JOIN {{ ref('fct_features_shopper') }} s
    ON fo.shopper_uuid = s.entity_id
    AND o.snapshot_date = s.snapshot_date  -- PIT: never omit
LEFT JOIN {{ ref('fct_features_merchant') }} m
    ON fo.merchant_id = m.entity_id
    AND o.snapshot_date = m.snapshot_date  -- PIT: never omit
