# Deliverable 01 — Build vs Buy Recommendation

**Effort:** ~3–4 hrs  
**Full document:** See \FeatureStore_BuildVsBuy_Recommendation_PUBLIC.docx\ in this folder

---

## Recommendation (TL;DR)

> **Adopt dbt-native now. Migrate to Feast when the online feature store becomes a
> concrete requirement. Do not adopt SageMaker Feature Store at this stage.**

---

## Options Evaluated

| | dbt-Native | Feast (OSS) | SageMaker FS |
|---|---|---|---|
| Setup complexity | Low | Medium | Medium-High |
| Team familiarity | High (SQL/dbt) | Low (new SDK) | Low-Medium |
| Batch support | Native | Good | Good |
| Online store (future) | ? Migration required | ? Config change only | ? Fully managed |
| Operational overhead | Minimal | Medium | Low-Medium (AWS managed) |
| Time to POC | 1–2 weeks | 3–5 weeks | 3–6 weeks |
| Cost (batch-only) | ~\–13/month | ~\–10/month | Can escalate with volume |

---

## Weighted Scoring

Weights reflect binding constraints: 1–2 person DE team, DS resistance to new tooling,
batch-only today, confirmed online store on the roadmap.

| Criteria | Weight | dbt-Native | Feast | SageMaker FS |
|---|---|---|---|---|
| Operational simplicity | 25% | 5/5 | 3/5 | 3/5 |
| Team familiarity / adoption | 20% | 5/5 | 2/5 | 3/5 |
| Future online store readiness | 20% | 2/5 | 5/5 | 5/5 |
| Time to value | 15% | 5/5 | 3/5 | 2/5 |
| PIT correctness | 10% | 3/5 | 5/5 | 5/5 |
| GDPR / PII controls | 10% | 4/5 | 2/5 | 4/5 |
| **Weighted Score** | | **4.1** | **3.3** | **3.6** |

---

## Why Not Feast Now

- DS team has signalled low appetite for new tooling — Feast SDK adds friction at the moment adoption needs to be maximised
- DE team of 1–2 cannot absorb the operational overhead of running a feature registry and online store
- 3–5 week POC vs 1–2 weeks for dbt-native

## Why Not SageMaker Feature Store

- Per-write/read/storage billing can escalate quickly at scale
- Console and SDK complexity the DE team doesn't need for batch-only
- Harder to migrate off than dbt-native ? Feast

## Why dbt-Native Now

- Zero new infrastructure — runs entirely in existing Airflow + dbt + Redshift + S3
- DS team already knows SQL; feature consumption via SELECT is the path of least resistance
- FeatureClient can be extended in days, not weeks
- GDPR/PII handled via existing Redshift IAM and column-level security

---

## Migration Path to Feast

Trigger migration when **any** of these conditions are met:

1. Online feature store becomes a concrete product requirement with a delivery date
2. DE team grows to 3+ engineers
3. PIT join complexity outgrows plain SQL snapshots
4. Feature count exceeds ~200 and catalog tooling is a bottleneck

The dbt-native architecture is designed to make this migration an evolution, not a rebuild.
See [02_architecture](../02_architecture/) for the deliberate design decisions that enable this.
