# Enterprise Real-Time Financial Fraud & Anomaly Detection System

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Kafka 3.6](https://img.shields.io/badge/Kafka-3.6.1%20KRaft-black.svg)](https://kafka.apache.org/)
[![Neo4j 5.26](https://img.shields.io/badge/Neo4j-5.26%20Community-008CC1.svg)](https://neo4j.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.3%20TypeScript-61DAFB.svg)](https://react.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5.1%20C2GAT-EE4C2C.svg)](https://pytorch.org/)

EGIS-SENTINEL is an end-to-end, enterprise financial fraud and anomaly intelligence platform. It bridges continuous high-throughput transaction streams with real-time stream processing, graph topological analysis, temporal graph neural network inference, and an interactive cybersecurity operations dashboard.

---

## 1. System Architecture

```
Banking Transactions (CSV / Replay Producer)
                   │
                   ▼
       Apache Kafka (Topic: transactions)
                   │
                   ▼
  Apache Flink (Validation & Timestamp Enrichment)
                   │
                   ▼
 Apache Kafka (Topic: processed_transactions)
         │                     │
         ▼                     ▼
 Neo4j Graph Ingestion   C2GAT ML & Rule Scoring
         │                     │
         ▼                     ▼
Graph Topology (4,380+)  Phase 5 + Phase 6 Scores
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
          FastAPI Backend (Port 8000)
             │              │
      REST Endpoints   WebSocket (/ws/transactions)
             │              │
             └──────┬───────┘
                    │
                    ▼
   React TypeScript Dashboard (Port 5173)
```

---

## 2. Core Capabilities & Phases

1. **Phase 1 — Ingestion & Data Validation:**
   - 2,512 transactions validated against a strict 16-column schema.
   - Comprehensive business rule enforcement (positive amounts, non-negative balances, valid access channels, zero duplicates).

2. **Phase 2 — Apache Kafka (KRaft Mode):**
   - High-throughput distributed message broker running natively in KRaft mode (no ZooKeeper dependency).
   - Dedicated partitions for raw `transactions` and enriched `processed_transactions`.

3. **Phase 3 — Apache Flink (PyFlink):**
   - Streaming pipeline validating incoming payloads, attaching ISO-8601 UTC `processing_timestamp` enrichment, and forwarding to processed topics.

4. **Phase 4 — Neo4j Graph Database:**
   - Property graph materialization of 4,380 nodes across `Account`, `Transaction`, `Device`, `IP`, and `Merchant`.
   - Rich relational edges (`PERFORMED`, `USED_DEVICE`, `ORIGINATED_FROM`, `PAID_TO`, `ACCESSED_VIA`, `CONNECTED_FROM`).

5. **Phase 5 — Graph-Based Risk Scoring:**
   - **Approach A (Normalized Composite, 0–100):** Continuous equal-weight aggregation of 6 topological features.
   - **Approach B (Rule Additive Points, 0–100):** Calibrated point accumulation for shared device/IP thresholds, velocity bursts, and network sprawl.

6. **Phase 6 — C2GAT-Inspired Temporal Graph Anomaly Detection:**
   - Deep unsupervised learning using Time2Vec temporal embeddings and Graph Attention (GAT) masked feature reconstruction.
   - Outputs continuous anomaly scores `[0.0, 1.0]` and tensor embedding norms.

7. **FastAPI Backend & WebSocket Streaming:**
   - Asynchronous REST API serving transactions, graph subgraphs, fraud alerts, and analytics.
   - Managed background Kafka consumer broadcasting live events via WebSocket `WS /ws/transactions`.

8. **Enterprise React Operations Dashboard:**
   - Real-time financial security dashboard featuring live telemetry tables, interactive SVG/Canvas network graph explorer, multi-model comparison analytics, and transaction investigation drawers.

---

## 3. Technology Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2, Pandas, Confluent-Kafka, Neo4j Python Driver, WebSockets.
- **Frontend:** React 18, TypeScript, Vite, Tailwind/Modern CSS, Lucide Icons.
- **Data & Streaming:** Apache Kafka 3.6.1 (KRaft), Apache Flink 2.1.3 (PyFlink), Neo4j Community 5.26.0.
- **Machine Learning:** PyTorch 2.5.1, Scikit-Learn, Time2Vec, Graph Attention Networks (C2GAT).

---

## 4. Repository Structure

```
fraud-detection-system/
├── backend/
│   ├── config.py                 # Environment & path configuration
│   ├── main.py                   # FastAPI app, lifespan & WebSocket endpoint
│   ├── routes/
│   │   ├── health.py             # Independent dependency health checks
│   │   ├── fraud.py              # Stats, transactions, detail, graph, alerts
│   │   └── analytics.py          # Risk distribution & model comparison
│   ├── schemas/
│   │   └── fraud.py              # Pydantic request & response models
│   ├── services/
│   │   ├── scoring_service.py    # Phase 5 & 6 score join and statistics
│   │   ├── transaction_service.py# In-memory indexing, search, filtering
│   │   ├── graph_service.py      # Parameterized Neo4j graph traversals
│   │   └── kafka_service.py      # Background consumer & WebSocket manager
│   └── tests/
│       └── test_api.py           # 12 automated backend unit & API tests
├── data/
│   ├── bank_transactions_data_2.csv # Raw transactional dataset
│   ├── transactions_clean.csv       # Clean validated dataset (2,512 rows)
│   └── validate_data.py             # Phase 1 validation specification script
├── flink/
│   ├── fraud_detection.py        # PyFlink streaming processing job
│   ├── smoke_test.py             # PyFlink verification test
│   └── conf/                     # JVM host configurations
├── frontend/
│   └── fraud-dashboard/          # Vite + React + TypeScript Dashboard
│       ├── src/
│       │   ├── App.tsx           # Main application state & WebSocket router
│       │   ├── api.ts            # Typed HTTP & WebSocket client
│       │   ├── types.ts          # TypeScript domain interfaces
│       │   ├── index.css         # Modern dark navy security design system
│       │   └── components/       # Overview, LiveTransactions, GraphExplorer, etc.
│       ├── package.json
│       └── vite.config.ts
├── ml/
│   ├── c2gat_inspired_model.py   # PyTorch Time2Vec + GAT neural network
│   ├── c2gat_model.pt            # Trained neural network weights
│   ├── c2gat_scaler.pkl          # Feature normalization scaler
│   ├── c2gat_scores.csv          # Precomputed unsupervised anomaly scores
│   └── verify_phase6.py          # 42 automated Phase 6 verification checks
├── native_services/              # Native Kafka & Flink startup helpers
├── neo4j/
│   ├── graph_loader.py           # Kafka -> Neo4j idempotent graph ingestion
│   ├── risk_scoring.py           # Phase 5 Approach A & B scoring engine
│   ├── scored_transactions.csv   # Scored transaction dataset with attribution
│   └── verify_risk_scoring.py    # Phase 5 verification script
├── producer/
│   └── transaction_producer.py   # Replay streaming producer to Kafka
├── scripts/
│   ├── check_environment.ps1     # Prerequisite diagnostic probe
│   ├── start_all.ps1             # Unified PowerShell startup orchestrator
│   └── stop_all.ps1              # Graceful shutdown script
├── tests/
│   └── test_e2e_pipeline.py      # Full 5-stage end-to-end integration test
├── DEMO_GUIDE.md                 # 10-minute presentation demonstration script
├── PROJECT_AUDIT.md              # Detailed repository audit
└── README.md
```

---

## 5. Prerequisites & Environment Setup

### Prerequisites
- **Windows 10 / 11 / Server** with PowerShell
- **Python 3.10+** (Python 3.12 recommended)
- **Node.js v18+** & npm (Node v24 tested)
- **Java 17 JDK** (Eclipse Adoptium JDK 17)
- **Native Kafka 3.6+** in `C:\kfk`
- **Native Neo4j 5.26+** in `C:\neo4j`

### Environment Configuration
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Default parameters in `.env`:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=fraud_detection_2026
KAFKA_BROKER=localhost:9092
KAFKA_INPUT_TOPIC=transactions
KAFKA_PROCESSED_TOPIC=processed_transactions
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
```

---

## 6. Service Startup & Orchestration

### Diagnostic Environment Check
```powershell
.\scripts\check_environment.ps1
```

### Start All Services
```powershell
.\scripts\start_all.ps1
```
This orchestrates and verifies:
1. Apache Kafka broker on `localhost:9092`
2. Neo4j Graph Database on `localhost:7687` (HTTP on `7474`)
3. FastAPI Backend on `http://127.0.0.1:8000`
4. React Dashboard on `http://localhost:5173`

### Stop Services
```powershell
.\scripts\stop_all.ps1
```

---

## 7. Testing & Verification

Run the full automated test suite:
```powershell
python -m pytest backend/tests/test_api.py tests/test_e2e_pipeline.py -v
```
*Result:* All 17 unit and integration tests pass cleanly.

Run specific phase regression tests:
```powershell
# Phase 1: Data validation
python data/validate_data.py

# Phase 5: Neo4j risk scoring verification
python neo4j/verify_risk_scoring.py

# Phase 6: C2GAT ML model & scores verification
python ml/verify_phase6.py

# Frontend build verification
cd frontend/fraud-dashboard
npm run build
```

---

## 8. Model Inference & Score Interpretation

### Approach A: Equal-Weight Normalized Composite (0–100)
A continuous composite score averaging 6 normalized indicators: shared device accounts, shared IP accounts, merchant cluster size, transaction amount soft-cap, 24h transaction velocity, and account network sprawl.

### Approach B: Rule-Based Additive Points (0–100)
A calibrated discrete point accumulation system allocating points for discrete threshold breaches:
- Dense shared device ($\ge 6$ accounts): **+25 pts**
- Dense shared IP ($\ge 8$ accounts): **+25 pts**
- High transaction amount ($> \$589.54$): **+20 pts**
- Rapid 24-hour velocity burst ($\ge 1$ tx): **+20 pts**
- High account network sprawl ($\text{degree} > 23$): **+10 pts**
- Dense merchant cluster ($\ge 30$ accounts): **+10 pts**

### Phase 6: C2GAT Anomaly Score (0.0–1.0)
An unsupervised reconstruction error normalized to `[0.0, 1.0]`. Captures multi-dimensional temporal and topological anomalies without requiring labeled fraud data.

> [!IMPORTANT]
> **Ground-Truth Assessment & Interpretability Notice:**
> The underlying banking dataset does not contain verified ground-truth fraud labels. Risk and anomaly scores represent structural anomalies and elevated operational risk patterns, **not** definitive proof of criminal fraud.

---

## 9. License & Attribution

Developed as an enterprise streaming fraud detection reference architecture.
Licensed under the Apache 2.0 License.
