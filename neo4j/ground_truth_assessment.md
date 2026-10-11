# Dataset Ground-Truth and Target Label Assessment

## Executive Summary
* **Final Ground-Truth Assessment**: **`Ground-truth label: NOT FOUND`**
* **Supervised Machine Learning Feasibility**: **NOT APPROPRIATE** under current data conditions.
* **Integrity Status**: No synthetic labels were created; no pseudo-labels were derived from risk scores; the source dataset remains completely untouched.

---

## 1. Dataset Files Inspected

The following dataset files and documentation sources in the repository were inspected:

1. **`data/bank_transactions_data_2.csv`**:
   * File size: 344,980 bytes
   * Shape: 2,512 rows, 16 columns
   * Description: Original input transactional CSV.
2. **`data/transactions_clean.csv`**:
   * File size: 347,493 bytes
   * Shape: 2,512 rows, 16 columns
   * Description: Validated transaction dataset produced by `data/validate_data.py`.
3. **`data/validate_data.py`**:
   * Official data ingestion and validation specification script defining the strict 16-column schema.
4. **`README.md`**:
   * Repository documentation detailing pipeline stages and dataset schema.

---

## 2. Dataset Schema (16 Columns)

Both dataset files share an identical 16-column schema with zero missing values across all 2,512 records:

| # | Column Name | Inferred Dtype | Unique Count | Null Count | Semantic Description |
| :-: | :--- | :---: | :---: | :---: | :--- |
| 1 | `TransactionID` | string (object) | 2,512 | 0 | Unique transaction identifier (`TX000001`–`TX002512`) |
| 2 | `AccountID` | string (object) | 495 | 0 | Originating account identifier (`AC00001`–`AC00500`) |
| 3 | `TransactionAmount` | float64 | 2,455 | 0 | Monetary transaction amount in dollars ($0.26 to $1,919.11) |
| 4 | `TransactionDate` | string / datetime | 2,512 | 0 | Timestamp of transaction occurrence |
| 5 | `TransactionType` | string (object) | 2 | 0 | Banking transaction type: `'Debit'` or `'Credit'` |
| 6 | `Location` | string (object) | 43 | 0 | Originating city location |
| 7 | `DeviceID` | string (object) | 681 | 0 | Client hardware identifier (`D000001`–`D000700`) |
| 8 | `IP Address` | string (object) | 592 | 0 | Originating IP network address |
| 9 | `MerchantID` | string (object) | 100 | 0 | Recipient merchant identifier (`M001`–`M100`) |
| 10 | `Channel` | string (object) | 3 | 0 | Access channel: `'Branch'`, `'ATM'`, or `'Online'` |
| 11 | `CustomerAge` | int64 | 63 | 0 | Account holder age (18 to 80) |
| 12 | `CustomerOccupation` | string (object) | 4 | 0 | Customer profession category |
| 13 | `TransactionDuration` | int64 | 288 | 0 | Session duration in seconds (10 to 300) |
| 14 | `LoginAttempts` | int64 | 5 | 0 | Number of login attempts prior to transaction (1 to 5) |
| 15 | `AccountBalance` | float64 | 2,510 | 0 | Remaining account balance ($10.50 to $14,997.80) |
| 16 | `PreviousTransactionDate` | string / datetime | 360 | 0 | Timestamp of the preceding transaction |

---

## 3. Candidate Label Columns & Provenance Analysis

Every categorical and discrete field was evaluated to ascertain whether it represents a disguised target variable:

### 3.1 `TransactionType`
* **Data Type**: String (`object`)
* **Unique Values**: 2 (`Debit`, `Credit`)
* **Distribution**:
  * `Debit`: 1,944 (77.39%)
  * `Credit`: 568 (22.61%)
* **Provenance**: Standard banking transaction classification (debiting or crediting an account).
* **Assessment**: **NOT A FRAUD LABEL**. Classifying debits as fraud or credits as legitimate has no semantic validity.

### 3.2 `Channel`
* **Data Type**: String (`object`)
* **Unique Values**: 3 (`Branch`, `ATM`, `Online`)
* **Distribution**:
  * `Branch`: 868 (34.55%)
  * `ATM`: 833 (33.16%)
  * `Online`: 811 (32.28%)
* **Provenance**: Transaction delivery interface. Balanced distribution across standard banking channels.
* **Assessment**: **NOT A FRAUD LABEL**. Delivery channel is an operational context feature.

### 3.3 `CustomerOccupation`
* **Data Type**: String (`object`)
* **Unique Values**: 4 (`Student`, `Doctor`, `Engineer`, `Retired`)
* **Distribution**:
  * `Student`: 657 (26.15%)
  * `Doctor`: 631 (25.12%)
  * `Engineer`: 625 (24.88%)
  * `Retired`: 599 (23.85%)
* **Provenance**: Demographic attribute.
* **Assessment**: **NOT A FRAUD LABEL**.

### 3.4 `LoginAttempts`
* **Data Type**: Integer (`int64`)
* **Unique Values**: 5 ($1, 2, 3, 4, 5$)
* **Distribution**:
  * $1$: 2,390 (95.14%)
  * $5$: 32 (1.27%)
  * $4$: 32 (1.27%)
  * $3$: 31 (1.23%)
  * $2$: 27 (1.07%)
* **Provenance**: Operational session authentication counter.
* **Assessment**: **NOT A FRAUD LABEL**. While elevated login attempts ($\ge 3$) indicate potential authentication friction or brute-force behavior, it is an exploratory behavioral feature, not an authoritative transaction fraud disposition.

### 3.5 Specific Absence of Target Fields
The dataset contains **no column** named:
* `is_fraud` / `IsFraud` / `Fraud`
* `Class` / `Label` / `Target`
* `TransactionStatus` / `Disposition` / `Chargeback`

---

## 4. Documentation & Schema Review

* **`data/validate_data.py`**:
  Lines 37–54 explicitly document `EXPECTED_COLUMNS` as exactly 16 fields. No target variable or ground-truth class is defined.
* **`README.md`**:
  Line 110 states:
  > *"This file keeps all original columns with correct data types applied. No fake columns are added."*
  Lines 138–147 outline the project architecture as a graph-based behavioral detection and risk-scoring pipeline ending in a dashboard:
  > *`Transaction CSV → Kafka → Apache Flink → Neo4j → Graph Analysis → Risk Score → Dashboard`*
  Machine learning supervised classification was never configured with a pre-existing target column in the repository.

---

## 5. Final Ground-Truth Assessment

```
Ground-truth label: NOT FOUND
```

Neither `data/bank_transactions_data_2.csv` nor `data/transactions_clean.csv` contains an explicit or implicit ground-truth fraud label.

---

## 6. Appropriateness of Supervised Machine Learning

> [!WARNING]
> **Supervised ML is Currently Inappropriate**:
> Training a supervised model (e.g. Random Forest, XGBoost, LightGBM, Logistic Regression) requires verified ground truth ($y$). In the absence of true labels:
> 1. Any attempt to train a supervised classifier would require **inventing labels** or **pseudo-labeling**.
> 2. Training a model on heuristic risk scores (e.g. Approach A or Approach B) merely trains the model to approximate the rule engine itself (a redundant circular model with distorted confidence).
> 3. Standard classification metrics ($F_1$-score, Precision, Recall, ROC-AUC) computed against pseudo-labels produce illusory validation metrics that do not measure genuine fraud detection efficacy.

---

## 7. Recommended Alternative Methodologies

Because no ground-truth label exists, the project should leverage one of the following legitimate options:

1. **Rule-Based & Graph-Based Risk Engine (Current Implementation)**:
   * Maintain the verified **Approach A** (normalized continuous index) and **Approach B** (additive point system) from Phase 5 Step 4.
   * Provide transparent, deterministic, and explainable risk scores without training black-box models.
2. **Unsupervised Anomaly Detection**:
   * If statistical/ML techniques are desired, employ **unsupervised methods** that do not require ground-truth labels:
     * Isolation Forest
     * One-Class SVM
     * Graph-based Local Outlier Factor (LOF)
     * Autoencoders
   * These models flag transactions based on multidimensional distance from normal population baselines rather than fictitious labels.
3. **Investigator-in-the-Loop Labeling (Active Learning)**:
   * Surface high-risk transactions (e.g. the 18 transactions triggering all 4 core graph patterns) to human domain experts via the dashboard to create verified ground-truth labels over time.
