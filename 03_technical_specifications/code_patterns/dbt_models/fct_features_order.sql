-- Entity: order (order_id)
-- Refresh: daily at 02:00 UTC via Airflow
-- Version: v1
-- Used by: Fraud, Credit Risk

{{ config(
    materialized='table',
    dist='order_id',
    sort='snapshot_date',
    tags=['feature_store', 'order', 'daily']
) }}

SELECT
    o.order_id                                                          AS entity_id,
    CURRENT_DATE                                                        AS snapshot_date,
    'v1'                                                                AS feature_version,
    CURRENT_TIMESTAMP                                                   AS created_at,
    -- Order features
    o.order_value                                                       AS order_value,
    o.n_instalments                                                     AS order_n_instalments,
    -- Cart features
    o.num_items                                                         AS cart_num_items,
    o.discount_amount                                                   AS cart_discount_amount,
    CASE WHEN o.discount_amount > 0 THEN 1 ELSE 0 END                  AS cart_has_discount,
    -- Device/session features
    o.platform                                                          AS device_platform,
    o.browser                                                           AS device_browser,
    -- Geographic features
    o.delivery_postal_code                                              AS geo_delivery_postal_code,
    o.distance_km                                                       AS geo_distance_km,
    -- Temporal features (cyclical encodings — avoids discontinuity at hour 23 ? 0)
    SIN(2 * PI() * EXTRACT(HOUR FROM o.created_at) / 24)               AS temporal_hour_sin,
    COS(2 * PI() * EXTRACT(HOUR FROM o.created_at) / 24)               AS temporal_hour_cos,
    EXTRACT(DOW FROM o.created_at)                                      AS temporal_day_of_week
FROM {{ ref('fact_orders') }} o
