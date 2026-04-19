"""
SageMaker Batch Transform — feature store integration
Shows how batch inference jobs load features for scoring
a full entity population (e.g., all active orders today).
"""
import boto3
import pandas as pd
from datetime import date
from feature_client import FeatureClient


def prepare_batch_input(
    entity: str,
    entity_ids: list,
    as_of_date: date,
    s3_output_path: str
):
    """
    Load features for a population of entities and write to S3
    for consumption by a SageMaker Batch Transform job.
    """
    client = FeatureClient()

    features_df = client.get_features(
        entity=entity,
        entity_ids=entity_ids,
        as_of_date=as_of_date,
    )

    # Drop metadata columns — keep only model input features
    drop_cols = ['snapshot_date', 'feature_version', 'created_at']
    feature_cols = [c for c in features_df.columns if c not in drop_cols]
    input_df = features_df[feature_cols]

    # Write to S3 as CSV for SageMaker Batch Transform input
    import awswrangler as wr
    wr.s3.to_csv(
        df=input_df,
        path=s3_output_path,
        index=False,
    )
    print(f"Batch input written: {len(input_df):,} rows ? {s3_output_path}")
    return s3_output_path


def launch_batch_transform(
    model_name: str,
    input_s3_path: str,
    output_s3_path: str,
    instance_type: str = 'ml.m5.xlarge',
):
    """Launch a SageMaker Batch Transform job."""
    sm = boto3.client('sagemaker')

    job_name = f"feature-store-batch-{date.today().isoformat()}"

    sm.create_transform_job(
        TransformJobName=job_name,
        ModelName=model_name,
        TransformInput={
            'DataSource': {'S3DataSource': {'S3DataType': 'S3Prefix', 'S3Uri': input_s3_path}},
            'ContentType': 'text/csv',
            'SplitType': 'Line',
        },
        TransformOutput={'S3OutputPath': output_s3_path},
        TransformResources={'InstanceType': instance_type, 'InstanceCount': 1},
    )

    print(f"Batch transform job launched: {job_name}")
    return job_name
