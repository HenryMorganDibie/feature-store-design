"""
SageMaker training job — feature store integration
Shows how a SageMaker training script loads features
via FeatureClient at the start of the training job.
"""
import argparse
import os
import pandas as pd
from datetime import date
from feature_client import FeatureClient


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain',     type=str, default='fraud')
    parser.add_argument('--start-date', type=str, default='2023-05-01')
    parser.add_argument('--end-date',   type=str, default='2024-05-31')
    parser.add_argument('--model-dir',  type=str, default=os.environ.get('SM_MODEL_DIR', '/opt/ml/model'))
    parser.add_argument('--output-dir', type=str, default=os.environ.get('SM_OUTPUT_DATA_DIR', '/opt/ml/output'))
    return parser.parse_args()


def main():
    args = parse_args()

    # Load training set from feature store
    client = FeatureClient()
    df = client.get_training_set(
        domain=args.domain,
        start_date=date.fromisoformat(args.start_date),
        end_date=date.fromisoformat(args.end_date),
    )
    print(f"Loaded {len(df):,} rows for domain: {args.domain}")

    # Separate features and label
    label_col = 'label'
    feature_cols = [c for c in df.columns if c not in [label_col, 'snapshot_date', 'order_id']]
    X = df[feature_cols]
    y = df[label_col]

    # --- Your model training logic here ---
    # e.g. xgb.train(...), sklearn.fit(...), etc.

    print(f"Training complete. Features used: {feature_cols}")


if __name__ == '__main__':
    main()
