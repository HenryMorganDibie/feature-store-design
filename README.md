# Feature Store Design: dbt-Native vs Feast on AWS

> **End-to-end feature store architecture for a BNPL fintech platform**
> Delivered across five workstreams for a client operating fraud detection,
> credit risk scoring, and debt collection ML models on AWS SageMaker.

---

## The Problem

A DS team of 4–10 engineers across three ML domains (Fraud, Credit Risk, Debt Collection)
was rebuilding the same features independently for every model. Estimated waste: **30–40%
of DS feature engineering time**. No shared layer, no discovery, no versioning, no PIT
correctness guarantees.

| Domain | Training Records | Features | Key Entities |
|---|---|---|---|
| Fraud Detection | ~1.7M | 154 | shopper, order |
| Credit Risk | ~2.9M | 150 | shopper, order |
| Debt Collection | ~26K | 30 | shopper |

Shared features across all three domains before this project: **zero**.

---

## Deliverables

| # | Deliverable | What It Covers |
|---|---|---|
| [01](./01_build_vs_buy/) | Build vs Buy Recommendation | dbt-native vs Feast vs SageMaker FS — scored against client constraints |
| [02](./02_architecture/) | Architecture Document | Storage, computation, SageMaker serving, catalog, monitoring, PIT strategy |
| [03](./03_technical_specifications/) | Technical Specifications | dbt model patterns, S3 layout, snapshot strategy, metadata schema |
| [04](./04_implementation_plan/) | Implementation Plan | Phased rollout — 10-week dbt-native or 16-week Feast path |
| [05](./05_open_questions/) | Open Questions | All 10 architectural questions answered: PIT, versioning, PII, governance |

Full documents (.PDF) for deliverables 01 and 02 are in their respective folders.

---

## Stack

| Component | Technology |
|---|---|
| Data warehouse | Amazon Redshift |
| Transformations | dbt (l0 Bronze ? l1 Silver ? l2 Gold) |
| Object storage | Amazon S3 |
| Orchestration | Apache Airflow |
| ML training & inference | Amazon SageMaker |
| Ingestion | Airbyte (3x daily) |
| Feature serving library | FeatureClient (Python, extended DataBridge) |

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| dbt-native first | Zero new infra; DS team already knows SQL; fastest adoption path |
| Entity-first tables | Same entity model Feast uses — migration is wrapping, not rebuilding |
| S3 as source of truth for snapshots | Feast offline store can point directly at this layout |
| FeatureClient abstraction layer | Identical DS API for both backends; migration = zero notebook changes |
| SageMaker batch transform integration | FeatureClient reads S3 directly from SageMaker notebooks and batch jobs |

---

## Author

**Henry Dibie** — Data Scientist & ML Systems Engineer
[linkedin.com/in/kinghenrymorgan](https://linkedin.com/in/kinghenrymorgan) | [github.com/HenryMorganDibie](https://github.com/HenryMorganDibie)

> *Client details redacted. All architecture, evaluation frameworks, and code patterns are original work.*
