# Phase 6 — Noise Robustness Test Report

> **PURPOSE**: This is a robustness-testing dataset ONLY.
> It does NOT replace `data/transactions_clean.csv` or `ml/features_unsupervised.csv`.
> It was NOT used for training. No fraud labels were created.

---

## Dataset Statistics

| Property | Value |
|---|---|
| Original rows | 2512 |
| Noise dataset rows | 2522 (includes 10 duplicates) |
| Random seed | 42 |
| Source | `data/transactions_clean.csv` (REAL dataset — unchanged) |

---

## Perturbations Applied

| # | Type | Column | Rows Affected | % Affected | Description |
|---|---|---|---|---|---|
| 1 | Missing Values | `TransactionAmount` | 12 | 0.48% | Set to NaN to simulate missing data |
| 2 | Whitespace Variation | `Location` | 25 | 1.0% | Added leading/trailing whitespace to simulate inconsistent ingestion |
| 3 | Duplicate Records | `All` | 10 | 0.4% | Appended 10 exact duplicate rows to simulate re-ingestion |
| 4 | Timestamp Format Variation | `TransactionDate` | 25 | 1.0% | Changed format from YYYY-MM-DD HH:MM:SS to DD/MM/YYYY HH:MM |
| 5 | Small Feature Perturbation | `TransactionAmount` | 50 | 1.99% | Added uniform ±1% jitter to TransactionAmount (harmless magnitude) |

---

## Noise Detection Test Results

| Check | Expected | Detected | Status |
|---|---|---|---|
| Missing TransactionAmount values | 12 | 12 | PASS |
| Whitespace rows in Location | 25 | 25 | PASS |
| Duplicate TransactionIDs | 10 | 10 | PASS |
| All timestamps parseable (dayfirst) | 2522 | 2522 | PASS |
| Original dataset unchanged | 2,512 rows, 0 nulls | Verified | PASS |

---

## Critical Invariants

- **Original dataset preserved**: `data/transactions_clean.csv` remains 2,512 rows with 0 modifications.
- **No fraud labels created**: No `is_fraud`, `fraud_flag`, or similar columns were added.
- **Not used for training**: This dataset was never passed to the C2GAT model.
- **No synthetic transactions**: All rows derive from real transactions; perturbations are data-quality variations only.

---

## Expected Pipeline Behavior

| Perturbation | Expected Behavior |
|---|---|
| Missing values | Preprocessing should detect and either impute or raise error |
| Whitespace | String stripping in preprocessing should normalize |
| Duplicate rows | Deduplication step should reduce to original count |
| Timestamp format | `pd.to_datetime(..., dayfirst=True)` parses all formats |
| Amount jitter ±1% | Values remain in valid positive range; model should be robust to small noise |

---

*Report generated: Phase 6 | Seed: 42*