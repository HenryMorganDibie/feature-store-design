# S3 Layout Reference

## Approach A: dbt-Native

\\\
s3://[client]-feature-store/
  features/
    shopper/snapshot_date=YYYY-MM-DD/part-00000.parquet
    order/snapshot_date=YYYY-MM-DD/part-00000.parquet
    merchant/snapshot_date=YYYY-MM-DD/part-00000.parquet
    training_sets/
      fraud/snapshot_date=YYYY-MM-DD/part-00000.parquet
      credit_risk/snapshot_date=YYYY-MM-DD/part-00000.parquet
      debt_collection/snapshot_date=YYYY-MM-DD/part-00000.parquet
  registry/feature_metadata.json
  audit/quality_reports/
\\\

## Approach B: Feast

\\\
s3://[client]-feature-store/
  feast/
    registry/registry.db
    offline/
      shopper/year=YYYY/month=MM/day=DD/part-00000.parquet
      order/year=YYYY/month=MM/day=DD/part-00000.parquet
      merchant/year=YYYY/month=MM/day=DD/part-00000.parquet
    sources/
      shopper/event_timestamp=YYYY-MM-DD/part-00000.parquet
      order/event_timestamp=YYYY-MM-DD/part-00000.parquet
      merchant/event_timestamp=YYYY-MM-DD/part-00000.parquet
\\\

## Retention Policy

- 365 days at S3 Standard: ~\.72/month for ~292 GB
- S3 Lifecycle rule to Glacier after 365 days (~\.004/GB/month)
- Cost is identical regardless of dbt-native or Feast approach
