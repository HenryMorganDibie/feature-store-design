"""
FeatureClient — Feast backend
Wraps the Feast Python SDK.
DS-facing API is identical to the dbt-native backend.
A migration from dbt-native to Feast requires only swapping this implementation.
"""
from feast import FeatureStore
import pandas as pd
from datetime import date, datetime
from typing import List, Optional


def get_domain_features(store: FeatureStore, domain: str) -> List[str]:
    """
    Generate the feature list for a domain directly from the Feast registry.
    Avoids a manually maintained dict that drifts out of sync with FeatureViews.
    FeatureViews must be tagged with domain in feature_views.py, e.g.:
      tags={'domain': 'fraud,credit_risk,debt_collection'}
    """
    features = []
    for fv in store.list_feature_views():
        if domain in fv.tags.get('domain', '').split(','):
            features.extend([f'{fv.name}:{f.name}' for f in fv.features])
    return features


class FeatureClient:
    def __init__(self, repo_path: str = '/opt/feast_repo'):
        self.store = FeatureStore(repo_path=repo_path)

    def get_features(
        self,
        entity: str,
        entity_ids: List[str],
        as_of_date: Optional[date] = None,
        **kwargs
    ) -> pd.DataFrame:
        ts = datetime.combine(as_of_date or date.today(), datetime.min.time())
        entity_df = pd.DataFrame({'entity_id': entity_ids, 'event_timestamp': ts})
        fv = self.store.get_feature_view(f'{entity}_features')
        features = [f'{entity}_features:{f.name}' for f in fv.features]
        return self.store.get_historical_features(
            entity_df=entity_df,
            features=features
        ).to_df()

    def get_training_set(
        self,
        domain: str,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> pd.DataFrame:
        entity_df = self._build_entity_df(domain, start_date, end_date)
        features = get_domain_features(self.store, domain)
        return self.store.get_historical_features(
            entity_df=entity_df,
            features=features
        ).to_df()

    def list_features(self, entity: str) -> pd.DataFrame:
        fv = self.store.get_feature_view(f'{entity}_features')
        return pd.DataFrame([
            {'name': f.name, 'dtype': str(f.dtype)}
            for f in fv.features
        ])

    def _build_entity_df(
        self, domain: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Build entity_df for a domain training set.
        Replace with actual Redshift/S3 query for your domain and date range.
        """
        raise NotImplementedError(
            "Implement _build_entity_df: query order IDs and timestamps "
            "for the domain and date range from Redshift or S3."
        )
