"""
FeatureClient — dbt-native backend
Reads S3 Parquet snapshots via awswrangler.
DS-facing API is identical to the Feast backend.
A future migration to Feast requires zero changes to DS notebooks.
"""
import awswrangler as wr
import pandas as pd
from datetime import date
from typing import List, Optional


class FeatureClient:
    S3_BASE = 's3://[client]-feature-store/features'

    def get_features(
        self,
        entity: str,
        entity_ids: List[str],
        as_of_date: Optional[date] = None,
        feature_version: str = 'v1',
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get features for a list of entity IDs as of a specific date.
        Defaults to the latest available snapshot if as_of_date is not provided.
        PIT correctness is enforced here — DS never writes the join condition directly.
        """
        snapshot = as_of_date or self._latest_snapshot(entity)
        df = wr.s3.read_parquet(
            path=f'{self.S3_BASE}/{entity}/snapshot_date={snapshot}/',
            dataset=True,
            filters=[
                ('entity_id', 'in', entity_ids),
                ('feature_version', '=', feature_version),
            ]
        )
        if columns:
            return df[['entity_id', 'snapshot_date'] + columns]
        return df

    def get_training_set(
        self,
        domain: str,
        start_date: date,
        end_date: date,
        feature_version: str = 'v1'
    ) -> pd.DataFrame:
        """
        Get a PIT-correct training set for a domain across a date range.
        PIT correctness is enforced at the SQL level in the training set dbt models.
        """
        return wr.s3.read_parquet(
            path=f'{self.S3_BASE}/training_sets/{domain}/',
            dataset=True,
            filters=[
                ('snapshot_date', '>=', str(start_date)),
                ('snapshot_date', '<=', str(end_date)),
                ('feature_version', '=', feature_version),
            ]
        )

    def list_features(self, entity: str) -> pd.DataFrame:
        """Return the feature catalog for an entity from the Redshift registry."""
        # Query feature_store.feature_registry in Redshift
        # Replace with your Redshift connection (e.g. redshift_connector or sqlalchemy)
        raise NotImplementedError("Connect to Redshift feature_store.feature_registry.")

    def _latest_snapshot(self, entity: str) -> str:
        """Find the most recent available S3 snapshot partition for an entity."""
        objects = wr.s3.list_objects(
            path=f'{self.S3_BASE}/{entity}/',
            suffix='.parquet'
        )
        dates = sorted(set(
            p.split('snapshot_date=')[1].split('/')[0]
            for p in objects
            if 'snapshot_date=' in p
        ))
        if not dates:
            raise ValueError(f'No snapshots found for entity: {entity}')
        return dates[-1]
