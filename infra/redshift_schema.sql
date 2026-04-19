-- Feature store schema and access control
-- Reference only — adapt to your Redshift environment

CREATE SCHEMA IF NOT EXISTS feature_store;

-- Feature registry (dbt-native approach)
CREATE TABLE IF NOT EXISTS feature_store.feature_registry (
    feature_id          VARCHAR(100)  NOT NULL,
    entity              VARCHAR(50)   NOT NULL,
    feature_version     VARCHAR(10)   NOT NULL,
    description         VARCHAR(500),
    domains             VARCHAR(200),
    owner               VARCHAR(100),
    is_pii              BOOLEAN       DEFAULT FALSE,
    gdpr_category       VARCHAR(100),
    access_role         VARCHAR(100),
    is_deprecated       BOOLEAN       DEFAULT FALSE,
    deprecated_date     DATE,
    successor_feature   VARCHAR(100),
    created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (feature_id, feature_version)
);

-- Roles
CREATE ROLE ds_standard_role;
CREATE ROLE ds_privileged_role;

-- Standard access
GRANT SELECT ON feature_store.fct_features_shopper  TO ds_standard_role;
GRANT SELECT ON feature_store.fct_features_order    TO ds_standard_role;
GRANT SELECT ON feature_store.fct_features_merchant TO ds_standard_role;

-- Revoke privileged columns from standard role
REVOKE SELECT (bureau_score, unpaid_balance, operations_count)
    ON feature_store.fct_features_shopper FROM ds_standard_role;

-- Grant privileged columns to privileged role only
GRANT SELECT (bureau_score, unpaid_balance, operations_count)
    ON feature_store.fct_features_shopper TO ds_privileged_role;
