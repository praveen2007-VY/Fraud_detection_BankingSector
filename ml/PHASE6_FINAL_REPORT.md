# PHASE 6 FINAL REPORT
## C2GAT-Inspired Self-Supervised Dynamic Graph Learning

**Project**: Real-Data Financial Fraud/Anomaly Detection System  
**Phase**: 6 — ML Model  
**Date**: 2026-09-26  
**Status**: COMPLETE — PASS

---

## 1. What Was Implemented

A **C2GAT-inspired self-supervised transaction anomaly detection** system using:
- Continuous-time encoding (Time2Vec)
- Multi-head graph attention over temporal transaction neighborhoods
- Masked feature reconstruction as the self-supervised learning objective
- Fully unlabeled training — no fraud labels created or used

> **Disclaimer**: This is a C2GAT-inspired adaptation for unlabeled transaction anomaly detection, NOT a reproduction of the original C2GAT fraud-classification system.

---

## 2. Files Created

| File | Purpose |
|---|---|
| [`ml/c2gat_inspired_design.md`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/c2gat_inspired_design.md) | 15-section design document |
| [`ml/temporal_graph_data.py`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/temporal_graph_data.py) | Temporal graph builder + temporal feature extraction |
| [`ml/build_temporal_graph.py`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/build_temporal_graph.py) | Standalone graph build + NPZ cache |
| [`ml/c2gat_inspired_model.py`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/c2gat_inspired_model.py) | PyTorch model: Time2Vec, GraphAttention, Encoder, Decoder |
| [`ml/train_c2gat_inspired.py`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/train_c2gat_inspired.py) | Training pipeline with chronological split and early stopping |
| [`ml/evaluate_c2gat_inspired.py`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/evaluate_c2gat_inspired.py) | Inference + anomaly score generation + Phase-5 comparison |
| [`ml/verify_phase6.py`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/verify_phase6.py) | 42-check PASS/FAIL verification script |
| [`ml/noise_test_report_generator.py`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/noise_test_report_generator.py) | Noise robustness test generator |
| [`ml/c2gat_comparison.md`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/c2gat_comparison.md) | Phase 5 vs Phase 6 comparison report |
| [`ml/noise_test_report.md`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/noise_test_report.md) | Noise robustness test report |
| [`ml/c2gat_model.pt`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/c2gat_model.pt) | Trained model state dict |
| [`ml/c2gat_scaler.pkl`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/c2gat_scaler.pkl) | Fitted StandardScaler (train set only) |
| [`ml/c2gat_scores.csv`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/c2gat_scores.csv) | Anomaly scores for all 2,512 transactions |
| [`ml/c2gat_train_log.csv`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/c2gat_train_log.csv) | Loss curve (84 epochs) |
| [`ml/temporal_graph_cache.npz`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/temporal_graph_cache.npz) | Cached graph neighbor matrix |
| [`data/transactions_noise_test.csv`](file:///C:/Users/Admin/Desktop/linkease/fraud-detection-system/data/transactions_noise_test.csv) | Separate noise robustness test dataset |

---

## 3. Files Modified

| File | Change |
|---|---|
| None | No existing Phase 1-5 files were modified |

---

## 4. Dataset Statistics

| Property | Value |
|---|---|
| Original dataset | `data/bank_transactions_data_2.csv` — **unchanged** |
| Clean dataset | `data/transactions_clean.csv` — **unchanged** (2,512 rows) |
| Feature matrix | `ml/features_unsupervised.csv` — **unchanged** (2,512 rows, 15 ML features) |
| Phase-5 scores | `neo4j/scored_transactions.csv` — **unchanged** (2,512 rows) |
| Transaction date range | 2023-01-02 to 2024-01-01 (365 days) |
| Unique accounts | 495 |
| Unique devices | 681 |
| Unique IPs | 592 |
| Unique merchants | 100 |

---

## 5. Model Architecture

```
Input: x_i ∈ R^15 (15 ML features, standardized), t_i (timestamp)

Feature Encoder:    Linear(15→32) + ReLU + Dropout(0.1)
Time2Vec:           Linear + sin(w_k*t + phi_k) → R^16
Graph Attention:    2-head attention over k=10 temporal neighbors
                    query_dim = 48 (feat=32 + time=16)
Fusion:             concat[h_i(32), e_i(16), context(48)] = 96 → Linear → R^64
Decoder:            Linear(64→15)

Self-supervised:    MSE(x_masked, x_hat_masked)  [30% mask ratio]

Total parameters:   15,815
```

---

## 6. Training Configuration

| Parameter | Value |
|---|---|
| Random seed | 42 |
| Train samples | 2,009 (chronologically first 80%) |
| Val samples | 503 (chronologically last 20%) |
| Train period | 2023-01-02 to 2023-10-23 |
| Val period | 2023-10-23 to 2024-01-01 |
| Epochs trained | 84 (early stopped; patience=25) |
| Best epoch | 59 |
| Best val loss | 0.7339 |
| Initial val loss | 0.9755 |
| Convergence | **PASS** (val_loss decreased 24.8%) |
| Training time | ~70 seconds (CPU, PyTorch 2.5.1+cpu) |
| Batch size | 64 |
| Optimizer | Adam, lr=1e-3 |
| LR scheduler | ReduceLROnPlateau (patience=15, factor=0.5) |
| Mask ratio | 30% |

---

## 7. Self-Supervised Objective

**Method**: Masked Feature Reconstruction (Masked Autoencoding on tabular + graph features)

**Why selected**:
- Simplest scientifically defensible objective for 2,512 unlabeled tabular transactions
- No label requirements
- Natural anomaly signal: poorly-reconstructed = unusual feature pattern
- Direct applicability to tabular data
- Well-established in BERT, MAE, TabNet literature

**NOT selected** (and why):
- Graph contrastive: augmentation strategy non-trivial without labels; risk of collapse
- Temporal contrastive: positive/negative pair construction complex at this scale
- Context prediction: insufficient neighborhood density for 2,512 samples

---

## 8. Evaluation Results

> No classification metrics (accuracy/F1/ROC-AUC) computed — no fraud labels exist.

### Training Behavior
- Train loss: 1.032 → 0.739 (converged)
- Val loss: 0.975 → 0.734 (converged, no overfitting)
- Early stopped at epoch 84 (best at epoch 59)

### Anomaly Score Distribution
| Percentile | C2GAT Score |
|---|---|
| p50 | 0.70 |
| p75 | 1.90 |
| p90 | 3.98 |
| p95 | 6.73 |
| p99 | 25.77 |
| p100 | 100.00 |

Right-skewed distribution (as expected for anomaly detection): vast majority near 0, small tail of unusual transactions.

### Embedding Statistics
- min norm: 0.850 | max: 8.906 | mean: 1.816 | std: 0.571

### Phase-5 Comparison
- Spearman rho (vs Approach A): 0.1912 (p < 0.0001)
- Spearman rho (vs Approach B): 0.2837 (p < 0.0001)
- Top-50 overlap with Approach A: 10 / 50 (20%)
- Top-50 overlap with Approach B: 9 / 50 (18%)

---

## 9. Top Anomaly Statistics

**Top 6 transactions** (C2GAT score > 89):

| TransactionID | Account | Date | C2GAT | Approach B |
|---|---|---|---|---|
| TX002405 | **AC00150** | 2023-02-27 | 100.00 | 60 |
| TX001078 | **AC00331** | 2023-10-30 | 99.51 | 70 |
| TX001618 | **AC00331** | 2023-10-30 | 97.52 | 50 |
| TX000585 | **AC00150** | 2023-02-27 | 95.43 | 70 |
| TX002310 | **AC00331** | 2023-10-31 | 92.94 | 60 |
| TX002452 | **AC00150** | 2023-02-28 | 89.43 | 50 |

**Key observation**: Top 6 anomalies cluster into just 2 accounts (AC00150, AC00331), each with multiple transactions in tight 1-2 day windows. This temporal clustering was detected by the C2GAT model's continuous-time encoding.

---

## 10. Comparison with Phase 5

- C2GAT agrees with Phase-5 on some high-risk accounts (AC00150, AC00331)
- C2GAT identifies 36/50 top-anomaly transactions NOT in Phase-5 top-50 — capturing patterns rules did not encode
- Phase-5 remains high-explainability (explicit rule attribution); C2GAT adds learned signals
- Neither is ground truth; both are complementary risk signals

---

## 11. Limitations

1. **No ground truth**: Cannot compute precision/recall. Anomaly = learned risk signal.
2. **Small dataset**: 2,512 transactions limits model capacity and neighborhood density.
3. **CPU-only**: GPU build has DLL init error; training ran on CPU (~70s — acceptable at this scale).
4. **PreviousTransactionDate excluded**: Found to be futuristic (2024-11-04 range vs. 2023 transactions) — excluded from all analysis.
5. **Hour/day range**: Transactions only occur at hours 16-18, weekdays Mon-Fri — `hour_of_day` and `day_of_week` features have limited discriminative power.
6. **30% fixed eval mask** selected features `shared_device_accounts` and `rapid_velocity_count_24h` — results may change with different mask selections.

---

## 12. Reproducibility

| Item | Value |
|---|---|
| Python | 3.12.10 |
| PyTorch | 2.5.1+cpu |
| numpy | 2.1.3 |
| scikit-learn | 1.9.1 |
| scipy | 1.18.0 |
| networkx | 3.6.1 |
| Random seed | 42 (all random state) |
| Determinism verified | PASS (42/42 checks) |

To reproduce: `python ml/train_c2gat_inspired.py` → `python ml/evaluate_c2gat_inspired.py`

---

## 13. Noise Robustness Test

**Noise dataset**: `data/transactions_noise_test.csv` (2,522 rows — 2,512 original + 10 duplicates)

Perturbations applied to SEPARATE copy only:
| Type | Rows | % |
|---|---|---|
| Missing TransactionAmount | 12 | 0.48% |
| Whitespace in Location | 25 | 1.0% |
| Duplicate records | 10 | 0.4% |
| Timestamp format variation | 25 | 1.0% |
| Amount ±1% jitter | 50 | 1.99% |

All noise detection tests: **PASS**  
Original dataset: **UNCHANGED** (2,512 rows, 0 nulls)

---

## PHASE 6 STATUS

| Requirement | Status |
|---|---|
| Real dataset preserved | **PASS** |
| Temporal graph built | **PASS** (2,512 nodes, 21,414 edges) |
| Model implementation | **PASS** (15,815 parameters) |
| Self-supervised training | **PASS** (val_loss converged 0.975→0.734) |
| Anomaly scoring | **PASS** (2,512 scores, [0,100], no NaN) |
| Phase-5 comparison | **PASS** (Spearman rho reported, no ground truth claim) |
| Noise robustness test | **PASS** (5 perturbation types detected) |
| Verification script | **PASS** (42/42 checks) |
| No fraud labels invented | **PASS** |
| No synthetic transactions | **PASS** |
| Reproducible | **PASS** (determinism verified) |
| **Overall Phase 6** | **PASS** |

---

> Phase 7 (FastAPI + Dashboard integration) may proceed.
