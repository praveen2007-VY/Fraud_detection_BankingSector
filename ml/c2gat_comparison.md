# C2GAT-Inspired Model vs Phase-5 Risk Scoring Comparison
## Phase 6 Analysis Report

> **Important Note**: This is a comparison of risk signals, not a competition with ground truth.
> Phase-5 scores are rule-based heuristics. C2GAT anomaly scores are learned representations.
> Neither represents confirmed fraud labels. Do not declare a "winner."

---

## 1. Method Comparison Table

| Component | Phase 5 | Phase 6 (C2GAT-Inspired) |
|---|---|---|
| Rule-based | Yes | No |
| Learned from data | No | Yes |
| Graph-aware | Yes | Yes |
| Temporal-aware | Limited (velocity only) | Yes (continuous-time encoding, inter-tx gap, rolling count) |
| Self-supervised | No | Yes |
| Requires fraud labels | No | No |
| Explainability | High (explicit rules) | Preserve graph context (attention weights) |
| Learned representation | No | Yes (64-dim latent embedding) |
| Computationally expensive | Low (rule lookup) | Moderate (GNN training ~70s on CPU) |
| Produces embedding | No | Yes (c2gat_embedding_norm) |
| Anomaly score type | Additive heuristic (0-100) | Reconstruction-based (normalized 0-100) |

---

## 2. Score Correlation Analysis

> Based on 2,512 real transactions | Spearman rank correlation (rho)

| Comparison | rho | p-value | Interpretation |
|---|---|---|---|
| C2GAT vs Approach A | **0.1912** | < 0.0001 | Statistically significant, weak positive alignment |
| C2GAT vs Approach B | **0.2837** | < 0.0001 | Statistically significant, weak positive alignment |

**Interpretation**: The positive significant correlation indicates the C2GAT model partially agrees with rule-based indicators, particularly Approach B (which uses threshold rules similar to what the model learns). However, the weak correlation (~0.19–0.28) shows substantial divergence — the model is capturing patterns beyond the explicit rules.

---

## 3. Top-N Rank Overlap

> Top 50 transactions (≈2% of 2,512)

| Comparison | Overlapping Transactions |
|---|---|
| C2GAT top-50 ∩ Approach A top-50 | **10 transactions** (20% overlap) |
| C2GAT top-50 ∩ Approach B top-50 | **9 transactions** (18% overlap) |
| C2GAT top-50 only (not in A or B top-50) | **36 transactions** (72% unique) |

**Observation**: The C2GAT model identifies a largely different set of high-anomaly transactions from either Phase-5 approach. This makes sense:
- Phase-5 flagged transactions that hit explicit graph topology thresholds (dense device/IP sharing)
- C2GAT flags transactions that are difficult to reconstruct — i.e., unusual feature combinations not well-represented in the training distribution

---

## 4. Top 10 C2GAT Anomalous Transactions

> Note: These are transactions where the model had highest reconstruction error.
> This does NOT confirm fraud. It means these transactions had feature patterns
> learned less well by the model (potentially unusual combinations).

| Rank | TransactionID | Account | Timestamp | C2GAT Score | Approach A | Approach B |
|---|---|---|---|---|---|---|
| 1 | TX002405 | AC00150 | 2023-02-27 17:52:43 | 100.00 | 55.97 | 60 |
| 2 | TX001078 | AC00331 | 2023-10-30 16:45:47 | 99.51 | 62.57 | 70 |
| 3 | TX001618 | AC00331 | 2023-10-30 18:14:15 | 97.52 | 46.97 | 50 |
| 4 | TX000585 | AC00150 | 2023-02-27 18:23:11 | 95.43 | 59.73 | 70 |
| 5 | TX002310 | AC00331 | 2023-10-31 16:05:00 | 92.94 | 51.96 | 60 |
| 6 | TX002452 | AC00150 | 2023-02-28 17:37:48 | 89.43 | 46.62 | 50 |
| 7 | TX002018 | AC00453 | 2023-02-17 16:57:32 | 30.27 | 56.33 | 80 |
| 8 | TX001514 | AC00416 | 2023-10-30 17:07:54 | 28.80 | 42.85 | 60 |
| 9 | TX001944 | AC00213 | 2023-04-03 16:35:30 | 28.77 | 48.53 | 70 |
| 10 | TX000953 | AC00295 | 2023-11-29 16:46:49 | 28.48 | 46.37 | 60 |

---

## 5. Notable Temporal Observations

### Account Cluster — AC00150
- Transactions TX002405, TX000585, TX002452 all from account **AC00150**
- All occur in a **2-day window**: 2023-02-27 to 2023-02-28
- C2GAT captures this burst as unusual — temporal graph shows these transactions as tight temporal neighbors with similar feature patterns but unusual reconstruction

### Account Cluster — AC00331
- Transactions TX001078, TX001618, TX002310 all from account **AC00331**
- All occur on **2023-10-30 to 2023-10-31** (two consecutive days)
- Three transactions in <26 hours — high temporal density for one account
- Phase-5 already flagged these moderately (scores 47-63)
- C2GAT assigns highest anomaly scores in dataset to these — the rapid succession pattern is learned as reconstruction-difficult

---

## 6. Graph Behavior — Top Anomalies

All top-6 C2GAT anomalies belong to just 2 accounts (AC00150, AC00331):
- This suggests the C2GAT model is detecting **account-level behavioral clusters** where the combination of features + temporal density is unusual
- These accounts appear multiple times in short time windows with similar configurations — the model reconstructs these poorly because they don't match the typical single-transaction pattern

---

## 7. Anomaly Score Distribution

| Percentile | C2GAT Score | Approach A | Approach B |
|---|---|---|---|
| p50 (median) | 0.70 | ~34 | ~35 |
| p75 | 1.90 | ~43 | ~50 |
| p90 | 3.98 | ~55 | ~70 |
| p95 | 6.73 | ~61 | ~80 |
| p99 | 25.77 | ~70 | ~90 |
| p100 | 100.00 | 100.00 | 100.00 |

**Observation**: C2GAT scores are right-skewed with most transactions scoring near 0 and a long tail. This is expected behavior for a reconstruction-based anomaly score — the vast majority of transactions are "normal" (easy to reconstruct) and a small minority show unusual patterns.

---

## 8. Transactions Identified Differently

### High C2GAT, Lower Phase-5
These represent transactions flagged by the learned model but not prominently by rules:
- TX002405 (C2GAT: 100.0, Approach A: 55.97) — high model anomaly but moderate rule score
- TX002452 (C2GAT: 89.4, Approach A: 46.62) — model finds unusual pattern not captured by graph rules

**Possible explanation**: The model detected the unusual feature *combination* (e.g., temporal proximity + specific channel/amount pattern) without any single rule threshold being triggered prominently.

### High Phase-5, Lower C2GAT
- Transactions with high shared-device/IP rule scores that the model reconstructed easily — these may represent common patterns in the training data, even if rule-based indicators trigger

---

## 9. Key Analytical Findings

1. **Agreement on high-risk accounts**: C2GAT and Phase-5 both elevate AC00150 and AC00331 — consistent signal across methods.

2. **C2GAT captures temporal clustering**: The model's top anomalies cluster in 2-day account bursts — a temporal pattern that Phase-5's velocity metric captures only partially.

3. **Divergence is information**: The 72% of C2GAT top-50 transactions not in Phase-5 top-50 are candidates for investigation — the model has potentially identified patterns the rules did not encode.

4. **Both are risk signals**: Neither output is ground truth. An investigator should consider both signals jointly.

---

## 10. Limitations and Caveats

- C2GAT anomaly score is a **learned risk signal**, not a fraud probability
- Phase-5 scores are **rule-based heuristics**, not verified fraud labels
- Both methods are exploratory in the absence of confirmed fraud cases
- Correlation analysis is signal comparison only — Phase-5 is NOT used as ground truth
- The C2GAT model was trained on 2,009 transactions — limited dataset for a GNN
- The 30% fixed eval mask happened to select `shared_device_accounts` and `rapid_velocity_count_24h` as masked features — this may explain alignment with Phase-5's graph indicators

---

*Phase 6 Comparison Report | Real dataset: 2,512 transactions | No fraud labels used or created*
