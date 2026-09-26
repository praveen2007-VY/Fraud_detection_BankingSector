# Fraud Detection System

A real-time fraud detection pipeline built on:
**Transaction CSV → Kafka → Apache Flink → Neo4j → Graph Analysis → Risk Score → Dashboard**

---

## Project Structure

```
fraud-detection-system/
├── backend/          # FastAPI backend (future steps)
├── config/           # Shared configuration files
├── data/             # Raw data and validation scripts
│   ├── bank_transactions_data_2.csv   # Raw transaction dataset
│   ├── validate_data.py               # STEP 1 - Data validation script
│   └── transactions_clean.csv         # Output of validation (auto-generated)
├── flink/            # Apache Flink jobs (future steps)
├── frontend/         # Dashboard UI (future steps)
├── kafka/            # Kafka config & topics (future steps)
├── neo4j/            # Neo4j schema & queries (future steps)
├── producer/         # Kafka producer scripts (future steps)
├── requirements.txt  # Python dependencies
└── README.md
```

---

## STEP 1 — Data Ingestion & Validation

### What it does

The validation script (`data/validate_data.py`) performs these checks on the raw CSV:

| Check | Description |
|-------|-------------|
| Column presence | Verifies all 16 expected columns exist |
| Missing values | Detects blank or null cells in every column |
| Duplicate TransactionIDs | Flags rows with repeated IDs |
| Date validation | Converts `TransactionDate` and `PreviousTransactionDate` to datetime |
| Numeric validation | Converts `TransactionAmount`, `AccountBalance`, `CustomerAge`, `TransactionDuration`, `LoginAttempts` |
| Business rules | Checks amount > 0, balance >= 0, age in [1,120], duration >= 1, attempts >= 0 |
| Categorical checks | Validates `TransactionType` and `Channel` against allowed value sets |
| Uniqueness stats | Counts unique accounts, devices, IPs, merchants, locations, channels |

### Prerequisites

Make sure Python 3.8+ is installed and install dependencies:

```bash
pip install -r requirements.txt
```

### Run STEP 1 — Validation

Run from the **project root** directory:

```bash
python data/validate_data.py
```

### Expected Output

```
================================================================
  FRAUD DETECTION SYSTEM - STEP 1: DATA VALIDATION
================================================================
  Input : .../data/bank_transactions_data_2.csv
  Output: .../data/transactions_clean.csv

[OK] CSV loaded from: ...

------------------------------------------------------------
  COLUMN PRESENCE CHECK
------------------------------------------------------------
[OK] All 16 expected columns are present.

... (per-column validation results) ...

================================================
  TRANSACTION DATA VALIDATION SUMMARY
================================================
  Rows                  : 2513
  Columns               : 16
  Missing values        : 0
  Duplicate TxIDs       : 0
  Invalid dates         : 0
  Invalid numeric values: 0
  Unique accounts       : ...
  Unique devices        : ...
  Unique IPs            : ...
  Unique merchants      : ...
  Unique locations      : ...
  Unique channels       : ...
================================================

  Validation completed successfully.
  Clean dataset saved to:
  .../data/transactions_clean.csv
```

### Output File

If no critical issues are found, the script writes:

```
data/transactions_clean.csv
```

This file keeps **all original columns** with correct data types applied. No fake columns are added.

---

## STEP 2 (PHASE 1) — Kafka Infrastructure

The messaging backbone runs Kafka in **KRaft** mode without ZooKeeper dependencies.

### Configuration

- Managed via [`docker-compose.yml`](docker-compose.yml)
- Host port mapped: `localhost:9092`
- Internal network port: `kafka:29092`
- Automatically provisions the `transactions` topic on startup

### Commands

| Action | Command |
|---|---|
| **Start Kafka** | `docker compose up -d` |
| **Check Status** | `docker compose ps` |
| **Verify Topic** | `docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic transactions` |
| **Stop Kafka** | `docker compose down` |

For detailed Kafka setup details, see [`kafka/README.md`](kafka/README.md).

---

## Coming in Future Steps

| Step | Component | Description |
|------|-----------|-------------|
| 2b   | Producer  | Python script streaming transactions to Kafka `transactions` topic |
| 3    | Flink     | Real-time windowed processing & feature extraction |
| 4    | Neo4j     | Graph ingestion — accounts, devices, merchants as nodes |
| 5    | Analysis  | Graph-based fraud pattern detection |
| 6    | Dashboard | Real-time risk score visualization |

