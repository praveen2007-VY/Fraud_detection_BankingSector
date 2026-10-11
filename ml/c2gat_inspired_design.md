# C2GAT-Inspired Self-Supervised Dynamic Graph Learning
## Design Document — Phase 6

> **Disclaimer**: This is a **C2GAT-inspired adaptation** for unlabeled transaction anomaly detection, not a claim of reproducing the original C2GAT fraud-classification system. The original C2GAT paper (Continuous-time Context-Aware Graph Attention Transformer) was designed for supervised learning with known fraud labels. Our adaptation borrows conceptual elements — continuous-time encoding, graph attention, and context aggregation — and applies them to a fully self-supervised setting on 2,512 real, unlabeled transactions.

---

## 1. Problem Definition

We have 2,512 real bank transactions observed from **2023-01-02 to 2024-01-01**, each associated with:
- A unique account (495 distinct accounts)
- A device (681 devices), IP address (592 IPs), merchant (100 merchants)
- Tabular attributes: amount, duration, login attempts, channel, balance, age
- Pre-computed graph topology metrics (Phase 5): shared device/IP accounts, merchant cluster, velocity, network sprawl

**Goal**: Learn a transaction representation that captures graph context, temporal behavior, and feature interactions — such that anomalous transactions have meaningfully different representations from baseline transactions — without any fraud labels.

---

## 2. Why Supervised Fraud Classification Is Not Possible

| Constraint | Detail |
|---|---|
| No `is_fraud` column | Dataset has 16 raw columns; none is a fraud indicator |
| No external ground truth | No chargeback or confirmed-fraud dataset linked to these TransactionIDs |
| No verified pseudo-labels | Phase-5 risk scores are explainable heuristics, not verified outcomes |
| Data integrity rule | Converting heuristic scores to binary labels would introduce false ground truth |
| Dataset size | 2,512 transactions is too small for reliable supervised GNN training even with labels |

Therefore, **supervised classification (binary fraud/non-fraud) is architecturally impossible and methodologically inappropriate** for this dataset.

---

## 3. Why Self-Supervised Learning Is Used

Self-supervised learning (SSL) is chosen because:

1. **No labels required**: SSL learns useful representations from the data structure itself.
2. **Anomaly detection via representation space**: After SSL training, transactions that are poorly reconstructed or that have high embedding norms / high reconstruction error relative to their neighbors are candidates for anomaly flagging.
3. **Scientifically defensible**: SSL for tabular and graph data is a well-established research direction (GraphCL, BGRL, MVGRL, masked autoencoders).
4. **Preserves integrity**: We never convert risk scores to labels.

The specific objective selected is **Masked Feature Reconstruction** (a form of masked autoencoding adapted for tabular+graph data). Justification in Section 10.

---

## 4. C2GAT Concepts Being Adopted

The following conceptual elements from the C2GAT family of approaches are incorporated:

| C2GAT Concept | How We Adopt It |
|---|---|
| Continuous-time encoding | We encode transaction timestamps as learnable sinusoidal time embeddings (inspired by TGAT/Time2Vec) |
| Context-aware graph attention | We use a multi-head attention layer over a transaction's local graph neighborhood |
| Graph-structured transaction modeling | We build an explicit temporal transaction graph where edges connect transactions via shared accounts, devices, IPs, and merchants |
| Temporal neighborhood | Each transaction aggregates from its k most recent contextual neighbors |
| Feature-rich transaction representation | Input includes behavioral, financial, and graph topology features |

---

## 5. Concepts NOT Copied From C2GAT

| C2GAT Element | Our Decision |
|---|---|
| Supervised fraud binary classification head | **Not used** — we have no fraud labels |
| Link prediction between known fraud accounts | **Not used** — no labeled fraud accounts |
| Specific published model weights or training hyperparameters | **Not used** — our dataset/scale is entirely different |
| Exact published C2GAT architecture layers | **Not reproduced** — this is a lightweight research adaptation |

---

## 6. Input Features

### 6.1 ML Feature Columns (15 features — from `ml/features_unsupervised.csv`)

```
Raw/Behavioral (5):
  transaction_amount, transaction_duration, login_attempts,
  customer_age, account_balance

Derived (1):
  amount_to_balance_ratio

Graph Topology (5):
  shared_device_accounts, shared_ip_accounts, merchant_cluster_accounts,
  rapid_velocity_count_24h, account_network_sprawl_degree

Categorical Binary (4):
  is_credit, channel_atm, channel_online, channel_branch
```

**Excluded**: `transaction_id`, `account_id` (identifiers), `ref_approach_a_score`, `ref_approach_b_score` (reference-only benchmarks).

### 6.2 Temporal Input

- **Primary timestamp**: `TransactionDate` from `data/transactions_clean.csv`
- Range: 2023-01-02 to 2024-01-01 (365 days)
- All 2,512 transactions have unique timestamps

**Note**: `PreviousTransactionDate` was found to be synthetic/futuristic (all values in 2024-11-04 range, beyond the transaction range). It is **excluded** from temporal analysis.

---

## 7. Temporal Representation

### 7.1 Continuous-Time Embedding

Inspired by Time2Vec and TGAT, we encode each timestamp as a combination of:
- **Absolute time normalization**: `t_norm = (t - t_min) / (t_max - t_min)` in [0,1]
- **Sinusoidal basis**: `[sin(w_k * t_norm + phi_k)]` for k = 1..d/2

This allows the model to represent temporal patterns at multiple scales (daily, weekly, monthly).

### 7.2 Derived Temporal Features

We compute the following deterministic temporal features for each transaction:

| Feature | Formula | Meaning |
|---|---|---|
| `t_norm` | `(t - t_min) / (t_max - t_min)` | Position in dataset time window |
| `day_of_week` | `t.dayofweek / 6.0` | Weekly cycle (0=Mon, normalized) |
| `hour_of_day` | `t.hour / 23.0` | Intra-day cycle (normalized) |
| `month_of_year` | `(t.month - 1) / 11.0` | Monthly cycle (normalized) |
| `inter_tx_gap_norm` | `log1p(gap_seconds) / log1p(max_gap)` | Log-normalized time since previous account transaction |
| `rolling_tx_count_7d` | count of same-account tx in 7 day window | Short-window activity density |

All temporal features are computed deterministically from `TransactionDate` sorted chronologically.

---

## 8. Graph Representation

### 8.1 Transaction Graph Construction

Each transaction is a **node** in a temporal graph. Edges are drawn between transactions sharing:

| Edge Type | Condition | Weight Meaning |
|---|---|---|
| `SAME_ACCOUNT` | Same `AccountID` | High relevance — same behavioral entity |
| `SAME_DEVICE` | Same `DeviceID` | Hardware reuse — possible credential sharing |
| `SAME_IP` | Same `IP Address` | Network proximity — possible coordinated origin |
| `SAME_MERCHANT` | Same `MerchantID` | Commercial clustering |

**Temporal constraint**: Only edges to transactions **earlier in time** are considered for a given transaction's neighborhood (no future leakage).

### 8.2 Neighborhood Size

For computational tractability (2,512 nodes), we use a **k-nearest temporal neighbor** approach:
- For each transaction, retrieve up to `k=10` most recent transactions (chronologically earlier) sharing any entity.
- If fewer than k exist, pad with zero vectors (masked attention).

### 8.3 Graph Structure Verification

The graph is verified to:
- Contain exactly 2,512 nodes (one per transaction)
- Have directed temporal edges (past to present only)
- Contain no future leakage (edge t_j to t_i only if t_j < t_i)

---

## 9. Attention Mechanism

We use a **single-layer multi-head attention** (2 heads) over a transaction's k-hop neighborhood.

For transaction `i` with neighbor set `N(i)`:

```
alpha_ij = softmax( (W_q * h_i)^T (W_k * h_j) / sqrt(d_k) )
h_i' = sum_{j in N(i)} alpha_ij * (W_v * h_j)
```

Where:
- `h_j` = concatenation of [feature_embedding_j, time_embedding_j]
- `W_q, W_k, W_v` are learnable projection matrices
- `d_k` = key dimension

**Purpose**: The attention weights `alpha_ij` learn which neighbors (shared device/IP/merchant/account transactions) are most contextually relevant — consistent with C2GAT's context-aware design.

---

## 10. Self-Supervised Objective: Masked Feature Reconstruction

### 10.1 Objective Selection Rationale

We evaluated four candidate self-supervised objectives:

| Objective | Suitability for 2,512 unlabeled tabular transactions |
|---|---|
| **Masked Feature Reconstruction** | Direct — reconstruct masked tabular features; anomalies reconstruct poorly |
| Temporal Contrastive Learning | Requires careful positive/negative pair construction; complex for 2,512 samples |
| Graph Contrastive Learning | Augmentation strategy for graphs is non-trivial without labels; risk of collapse |
| Context Prediction | Requires sufficient neighborhood density; sparse at 2,512 samples |

**Selected**: **Masked Feature Reconstruction** — simplest, most scientifically defensible for tabular + graph data at this dataset size.

### 10.2 Masking Strategy

- During training, randomly mask **30%** of input feature dimensions per sample (random per forward pass).
- The encoder (with graph attention) observes the unmasked features + graph context.
- The decoder reconstructs the original values for the **masked** positions only.
- **Loss**: Mean Squared Error (MSE) on masked feature positions.

### 10.3 Anomaly Score Derivation

After training:
1. Apply the encoder on all 2,512 transactions with a **fixed deterministic mask** (same across all transactions).
2. Compute reconstruction loss for each transaction.
3. **Anomaly Score** = per-transaction reconstruction loss (higher = more anomalous).
4. Also compute `embedding_norm = ||z_i||_2` as supplementary signal.

---

## 11. Model Architecture

```
Input:
  x_i in R^15           (15 ML features, standardized)
  t_i in R              (timestamp, normalized)
  N(i) = {x_j, t_j}    (k temporal neighbors, k<=10)

Layer 1 - Feature Encoder:
  h_i = ReLU(Linear(15 -> 32))(x_i)

Layer 2 - Temporal Encoder:
  e_i = Time2Vec(t_i) in R^16

Layer 3 - Neighbor Embeddings (shared weights):
  h_j = ReLU(Linear(15 -> 32))(x_j) for each j in N(i)

Layer 4 - Graph Attention:
  query = concat([h_i; e_i])            [48]
  key_j = concat([h_j; e_j])            [48]
  val_j = Linear(48 -> 32)(key_j)       [32]
  alpha_ij = softmax(query * key_j^T / sqrt(48))
  c_i = sum_j alpha_ij * val_j          [32]  <- context

Layer 5 - Fusion:
  concat([h_i; e_i; c_i])               [80]
  z_i = ReLU(Linear(80 -> 64))(concat)  [64]  <- latent embedding

Layer 6 - Decoder:
  x_hat_i = Linear(64 -> 15)(z_i)       [15]  <- reconstruction

Self-Supervised Loss (masked positions only):
  L = MSE(x_i[mask], x_hat_i[mask])
```

**Total learnable parameters**: approximately 15,000 — appropriate for 2,512 training samples.

---

## 12. Training Procedure

| Hyperparameter | Value | Rationale |
|---|---|---|
| Random seed | 42 | Deterministic reproducibility |
| Feature standardization | StandardScaler (fit on train only) | Normalize to zero-mean unit-variance |
| Train/val split | Chronological 80/20 (2,010 train / 502 val) | Temporal ordering respected; no future leakage |
| Epochs | 150 (with early stopping) | Sufficient for convergence |
| Batch size | 64 | Balanced for 2,010 training samples |
| Optimizer | Adam, lr=1e-3 | Standard adaptive optimizer |
| LR scheduler | ReduceLROnPlateau (patience=15, factor=0.5) | Adaptive step reduction |
| Mask ratio | 0.30 | 30% features masked per training sample |
| Embedding dim | 64 | Latent space size |
| Attention heads | 2 | Diverse context aggregation |
| k-neighbors | 10 | Max temporal neighbors per transaction |
| Dropout | 0.1 | Mild regularization |
| Early stopping | Patience 25 | Prevent overfitting on small dataset |

---

## 13. Evaluation Methodology

Since there are **no verified fraud labels**, classification metrics (accuracy, F1, ROC-AUC) are **not applicable and not computed**.

### Data Integrity
- 2,512 transactions represented in output
- No duplicates, no NaNs in anomaly scores

### Training Behavior
- Loss curve convergence (train vs. val MSE per epoch)
- Final embedding statistics (mean, std, norm distribution)

### Anomaly Score Analysis
- Score distribution (percentiles p50, p75, p90, p95, p99)
- Top 1%, 5%, 10% anomalous transactions reported

### Temporal Behavior
- Time clustering of high-anomaly transactions

### Graph Behavior
- Device/IP/merchant patterns in top anomalies vs. baseline

### Phase-5 Comparison
- Spearman rank correlation with Approach A and Approach B scores
- Top-N rank overlap
- Disagreement analysis

---

## 14. Limitations

1. **No ground truth**: Cannot compute precision/recall/F1. Anomaly score is a learned risk signal.
2. **Small dataset**: 2,512 transactions limits graph density and model capacity.
3. **PreviousTransactionDate excluded**: Values are futuristic (2024-11-04 range) relative to transaction dates; likely synthetic — excluded from all temporal analysis.
4. **Interpretation**: High anomaly score means the transaction's feature pattern was learned less well — not that it is confirmed fraud.
5. **CPU-only**: PyTorch GPU build has DLL initialization error; training runs on CPU (appropriate at this scale).
6. **Neighborhood sparsity**: Some early transactions have no prior entity-sharing transactions.
7. **No streaming**: Phase 6 is batch; streaming is Phase 7.

---

## 15. Reproducibility Details

| Item | Value |
|---|---|
| Python | 3.12.10 |
| numpy | 2.1.3 |
| pandas | >=2.0.0 |
| scikit-learn | 1.9.1 |
| scipy | 1.18.0 |
| networkx | 3.6.1 |
| PyTorch | 2.5.1 (CPU) |
| Random seed | 42 (numpy, torch, random, Python builtins) |
| Dataset | `data/transactions_clean.csv` — 2,512 rows, unchanged |
| Feature matrix | `ml/features_unsupervised.csv` — pre-built, unchanged |
| Train/val split | Chronological: first 2,010 -> train, last 502 -> validation |
| Output | `ml/c2gat_scores.csv` |

---

*Document version: Phase 6.0 | Created: 2026-09-26*
