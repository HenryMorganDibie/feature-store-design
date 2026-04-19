"""
SageMaker notebook — FeatureClient usage patterns
Shows how DS engineers consume features in SageMaker notebooks
for both exploratory analysis and training set preparation.
"""
from feature_client import FeatureClient
from datetime import date
import pandas as pd

# -------------------------------------------------------------------
# Initialise FeatureClient
# Connects to dbt-native S3 backend or Feast transparently
# -------------------------------------------------------------------
client = FeatureClient()

# -------------------------------------------------------------------
# Pattern 1: Get a PIT-correct training set for the fraud domain
# For use in SageMaker training jobs and notebook experiments
# -------------------------------------------------------------------
fraud_df = client.get_training_set(
    domain='fraud',
    start_date=date(2023, 5, 1),
    end_date=date(2024, 5, 31),
)

print(f"Fraud training set: {len(fraud_df):,} rows, {len(fraud_df.columns)} features")
print(fraud_df.head())

# -------------------------------------------------------------------
# Pattern 2: Get features for specific entities as of a given date
# For point-in-time lookups during model development
# -------------------------------------------------------------------
shopper_features = client.get_features(
    entity='shopper',
    entity_ids=['uuid-001', 'uuid-002', 'uuid-003'],
    as_of_date=date(2024, 1, 15),
)

# -------------------------------------------------------------------
# Pattern 3: Browse the feature catalog before building new features
# Check what already exists before writing custom queries
# -------------------------------------------------------------------
catalog = client.list_features(entity='shopper')
print(catalog.to_string())

# -------------------------------------------------------------------
# Pattern 4: Chunked loading for large training sets
# Recommended for Credit Risk (~3.5 GB) on ml.m5.xlarge
# -------------------------------------------------------------------
date_ranges = [
    (date(2022, 1, 1), date(2022, 6, 30)),
    (date(2022, 7, 1), date(2022, 12, 31)),
    (date(2023, 1, 1), date(2023, 6, 30)),
    (date(2023, 7, 1), date(2023, 12, 31)),
    (date(2024, 1, 1), date(2024, 2, 28)),
]

chunks = [
    client.get_training_set('credit_risk', s, e)
    for s, e in date_ranges
]
credit_risk_df = pd.concat(chunks, ignore_index=True)
print(f"Credit Risk training set: {len(credit_risk_df):,} rows")
