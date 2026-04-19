-- Entity: shopper (uuid)
-- Refresh: daily at 02:00 UTC via Airflow
-- Version: v1
-- Used by: Fraud, Credit Risk, Debt Collection

{{ config(
    materialized='table',
    dist='uuid',
    sort='snapshot_date',
    tags=['feature_store', 'shopper', 'daily']
) }}

WITH shopper_history AS (
    SELECT
        s.uuid,
        COUNT(o.order_id)                                                          AS n_orders_lifetime,
        COUNT(CASE WHEN o.created_at >= DATEADD(day,-30,CURRENT_DATE) THEN 1 END)  AS n_orders_30d,
        COUNT(CASE WHEN o.created_at >= DATEADD(day,-90,CURRENT_DATE) THEN 1 END)  AS n_orders_90d,
        SUM(o.order_value)                                                          AS total_spend_lifetime,
        SUM(CASE WHEN o.created_at >= DATEADD(day,-30,CURRENT_DATE)
                 THEN o.order_value ELSE 0 END)                                    AS total_spend_30d,
        AVG(o.order_value)                                                          AS avg_order_value,
        DATEDIFF(day, MAX(o.created_at), CURRENT_DATE)                             AS days_since_last_order
    FROM {{ ref('dim_shoppers') }} s
    LEFT JOIN {{ ref('fact_orders') }} o ON s.uuid = o.shopper_uuid
    GROUP BY s.uuid
)

SELECT
    s.uuid                                              AS entity_id,
    CURRENT_DATE                                        AS snapshot_date,
    'v1'                                                AS feature_version,
    CURRENT_TIMESTAMP                                   AS created_at,
    -- Profile features
    DATEDIFF(year, s.date_of_birth, CURRENT_DATE)      AS shopper_age,
    s.province                                          AS shopper_province,
    DATEDIFF(day, s.registration_date, CURRENT_DATE)   AS shopper_tenure_days,
    -- History features
    h.n_orders_lifetime                                 AS shopper_n_orders_lifetime,
    h.n_orders_30d                                      AS shopper_n_orders_30d,
    h.n_orders_90d                                      AS shopper_n_orders_90d,
    h.total_spend_lifetime                              AS shopper_total_spend_lifetime,
    h.total_spend_30d                                   AS shopper_total_spend_30d,
    h.avg_order_value                                   AS shopper_avg_order_value,
    h.days_since_last_order                             AS shopper_days_since_last_order
FROM {{ ref('dim_shoppers') }} s
LEFT JOIN shopper_history h ON s.uuid = h.uuid
