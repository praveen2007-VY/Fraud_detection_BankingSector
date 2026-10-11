# ML Feature Schema for Unsupervised Anomaly Detection

## Overview
This document specifies the schema, definitions, transformations, and inclusion rationales for the feature dataset created at [ml/features_unsupervised.csv](file:///c:/Users/Admin/Desktop/linkease/fraud-detection-system/ml/features_unsupervised.csv).

The dataset integrates raw transactional session attributes from [data/transactions_clean.csv](file:///c:/Users/Admin/Desktop/linkease/fraud-detection-system/data/transactions_clean.csv) and topological graph metrics from [neo4j/scored_transactions.csv](file:///c:/Users/Admin/Desktop/linkease/fraud-detection-system/neo4j/scored_transactions.csv).

> [!IMPORTANT]
> **Data Leakage & Supervision Constraints**:
> - **No Ground-Truth Labels**: The dataset contains 0 target labels (no `is_fraud`, `Class`, etc.).
> - **No Pseudo-Labels**: Neither Approach A nor Approach B scores are used as training targets.
> - **No Identifier Leakage**: High-cardinality nominal identifiers (`transaction_id`, `account_id`) are excluded from model training inputs.
> - **Reference Benchmarks**: The columns `ref_approach_a_score` and `ref_approach_b_score` are retained strictly for post-hoc validation and comparative correlation against unsupervised anomaly scores.

---

## 1. Feature Catalog

The dataset contains **19 total columns**:
* **2 Identifier / Metadata Columns** (Excluded from ML)
* **15 Unsupervised ML Features** (11 Continuous/Count + 4 Binary)
* **2 Reference Benchmark Columns** (Excluded from ML training)

### Detailed Column Specifications

| # | Column Name | Source | Meaning | Data Type | Raw / Derived | Transformation Applied | Used by ML? | Inclusion Rationale |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| 1 | `transaction_id` | `transactions_clean.csv` | Primary transaction identifier | string | Raw | None | **NO** (Identifier) | Primary key for traceability and linking back to graph and raw events. |
| 2 | `account_id` | `transactions_clean.csv` | Account identifier | string | Raw | None | **NO** (Identifier) | Entity tracing; prevents the model from overfitting to specific accounts. |
| 3 | `transaction_amount` | `transactions_clean.csv` | Monetary value of the transaction in USD | float64 | Raw | None | **YES** | Outlier amounts are primary indicators of financial risk and capital exposure. |
| 4 | `transaction_duration` | `transactions_clean.csv` | Active session duration in seconds | int64 | Raw | None | **YES** | Extremely rapid sessions (scripted/bot transactions) or unnaturally lengthy sessions reflect behavioral anomalies. |
| 5 | `login_attempts` | `transactions_clean.csv` | Consecutive authentication attempts prior to transaction | int64 | Raw | None | **YES** | Elevated login attempts indicate brute force, password guessing, or authentication friction. |
| 6 | `customer_age` | `transactions_clean.csv` | Age of the account holder in years | int64 | Raw | None | **YES** | Contextual demographic baseline; extreme age discrepancies relative to amount/balance highlight anomalies. |
| 7 | `account_balance` | `transactions_clean.csv` | Current balance remaining in account | float64 | Raw | None | **YES** | Baseline financial cushion; contextualizes whether a transaction is disproportionate to account liquidity. |
| 8 | `amount_to_balance_ratio` | Engineered | Ratio of transaction amount to account balance: $\frac{\text{Amount}}{\text{Balance} + 1.0}$ | float64 | Derived | Ratio division with $+1.0$ epsilon smoothing | **YES** | Classic financial risk indicator; flags transactions that deplete or exceed available balance ($>1.0$). |
| 9 | `shared_device_accounts` | `neo4j` graph | Number of distinct accounts sharing the transaction device | int64 | Derived (Graph) | Subgraph aggregation: degree of `(:Device)<-[:ACCESSED_VIA]-(:Account)` | **YES** | Device multi-tenancy indicates credential stuffing, account takeover (ATO), or device farms. |
| 10 | `shared_ip_accounts` | `neo4j` graph | Number of distinct accounts sharing the transaction IP | int64 | Derived (Graph) | Subgraph aggregation: degree of `(:IP)<-[:CONNECTED_FROM]-(:Account)` | **YES** | IP multi-tenancy indicates VPNs, proxy nodes, or shared fraud rings. |
| 11 | `merchant_cluster_accounts` | `neo4j` graph | Number of distinct accounts transacting with the merchant | int64 | Derived (Graph) | Subgraph aggregation: distinct accounts transacting with `(:Merchant)` | **YES** | Measures merchant concentration; detects mule merchant aggregation or concentrated card-testing hubs. |
| 12 | `rapid_velocity_count_24h` | `neo4j` graph / timestamps | Count of other transactions by the same account within $\le 24$ hours | int64 | Derived (Temporal/Graph) | Windowed aggregation across account transaction history | **YES** | Burst transaction frequency indicates high-velocity cash-out attacks or automated script runs. |
| 13 | `account_network_sprawl_degree` | `neo4j` graph | Sum of distinct devices, IPs, and merchants linked to the account | int64 | Derived (Graph) | Sum of out-degrees: $\text{deg}(D) + \text{deg}(IP) + \text{deg}(M)$ | **YES** | Measures topological account dispersion; flags synthetic identities or compromised multi-entity sprawl. |
| 14 | `is_credit` | `transactions_clean.csv` | Binary indicator for credit transactions ($1 = \text{Credit}, 0 = \text{Debit}$) | int64 | Derived | Binary encoding from `TransactionType` | **YES** | Captures credit vs debit transaction modality. |
| 15 | `channel_atm` | `transactions_clean.csv` | Binary indicator: transaction conducted via ATM ($1 = \text{Yes}, 0 = \text{No}$) | int64 | Derived | One-hot encoding of `Channel` | **YES** | Channel modality: ATM transactions carry distinct physical-risk profiles. |
| 16 | `channel_online` | `transactions_clean.csv` | Binary indicator: transaction conducted Online ($1 = \text{Yes}, 0 = \text{No}$) | int64 | Derived | One-hot encoding of `Channel` | **YES** | Channel modality: Card-not-present online transactions carry distinct cyber-risk profiles. |
| 17 | `channel_branch` | `transactions_clean.csv` | Binary indicator: transaction conducted in Branch ($1 = \text{Yes}, 0 = \text{No}$) | int64 | Derived | One-hot encoding of `Channel` | **YES** | Channel modality: Physical in-person branch baseline. |
| 18 | `ref_approach_a_score` | `neo4j/scored_transactions.csv` | Approach A Normalized Composite Score ($0–100$) | float64 | Derived (Phase 5) | None | **NO** (Reference Benchmark) | Benchmark reference for post-hoc validation; MUST NOT be used as training feature or target. |
| 19 | `ref_approach_b_score` | `neo4j/scored_transactions.csv` | Approach B Rule-Based Additive Points ($0–100$) | float64 | Derived (Phase 5) | None | **NO** (Reference Benchmark) | Benchmark reference for post-hoc validation; MUST NOT be used as training feature or target. |

---

## 2. Categorical Variable Handling & Dimensionality Rationale

1. **`TransactionType`**:
   * Evaluated: 2 unique values (`Debit` 1,944, `Credit` 568).
   * Transformation: Encoded as single binary variable `is_credit` ($0/1$).
2. **`Channel`**:
   * Evaluated: 3 unique values (`Branch` 868, `ATM` 833, `Online` 811).
   * Transformation: One-hot encoded into 3 binary columns (`channel_atm`, `channel_online`, `channel_branch`) to allow tree algorithms (Isolation Forest) clean binary split boundaries.
3. **`CustomerOccupation`**:
   * Evaluated: 4 categories (`Student`, `Doctor`, `Engineer`, `Retired`), evenly distributed ($\approx 25\%$ each).
   * Decision: **Excluded from unsupervised feature set**. Demographic occupational labels do not provide direct transaction anomaly signals and adding 4 dummy variables risks distorting distance-based metrics (LOF, SVM) without behavioral justification.
4. **`Location`**:
   * Evaluated: 43 unique nominal cities.
   * Decision: **Excluded from unsupervised feature set**. One-hot encoding 43 locations would inject extreme sparsity (43 sparse dimensions on 2,512 rows) and risk arbitrary outlier flagging driven solely by city cardinality.

---

## 3. Trainable Feature Matrix Specification

When unsupervised models are trained in subsequent steps, the training matrix $X$ MUST consist strictly of the **15 selected features**:

```python
ML_FEATURE_COLS = [
    # Continuous / Numerical Features (6)
    "transaction_amount",
    "transaction_duration",
    "login_attempts",
    "customer_age",
    "account_balance",
    "amount_to_balance_ratio",

    # Graph Topological Features (5)
    "shared_device_accounts",
    "shared_ip_accounts",
    "merchant_cluster_accounts",
    "rapid_velocity_count_24h",
    "account_network_sprawl_degree",

    # Categorical Encoded Features (4)
    "is_credit",
    "channel_atm",
    "channel_online",
    "channel_branch"
]
```
