# Demonstration Guide: Real-Time Fraud & Anomaly Detection System

**System Name:** EGIS-SENTINEL Enterprise Fraud Detection Pipeline  
**Target Duration:** 5–10 Minutes  
**Platform:** Windows 11 / Windows Server (PowerShell)  
**Access URL:** [http://localhost:5173](http://localhost:5173)  

---

## 1. Quick Presentation Summary

EGIS-SENTINEL is an end-to-end, enterprise streaming financial fraud detection and anomaly detection system. It ingests high-throughput banking transactions, enriches them in real time via Apache Flink, materializes heterogeneous identity topologies in Neo4j, computes multi-signal graph topological risk scores (Phase 5), and generates unsupervised temporal graph anomaly embeddings via a C2GAT-inspired PyTorch neural network (Phase 6).

The system serves both real-time fraud alerts and investigative intelligence via a modular FastAPI backend and an interactive, security-focused React TypeScript dashboard.

---

## 2. Target Architecture

```
Banking Transactions (CSV / Replay Producer)
                   │
                   ▼
       Apache Kafka (transactions)
                   │
                   ▼
 Apache Flink (Validation & Timestamp Enrichment)
                   │
                   ▼
  Apache Kafka (processed_transactions)
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
        React Dashboard (Port 5173)
```

---

## 3. Pre-Flight Verification & Startup

### Step 1: Verify Environment
Open PowerShell in the repository root:
```powershell
.\scripts\check_environment.ps1
```
*Expected Outcome:* All 6 checks show `[PASS]`, and port bindings report `[LISTENING]`.

### Step 2: Start All Services (if not already running)
```powershell
.\scripts\start_all.ps1
```
*Expected Output:*
- Apache Kafka on `localhost:9092`
- Neo4j Graph DB on `localhost:7687` (HTTP on `7474`)
- FastAPI Backend on `http://127.0.0.1:8000`
- React Dashboard on `http://localhost:5173`

---

## 4. 10-Minute Live Demonstration Script

### Minute 0:00 – 1:30 | Mission Control & System Health
1. Open [http://localhost:5173](http://localhost:5173) in your browser.
2. Point out the top navigation status chips:
   - **Stream**: `LIVE` (pulsing green dot showing connected WebSocket).
   - **Kafka**: `READY` (broker port 9092).
   - **Neo4j**: `READY` (Bolt driver connected).
   - **C2GAT**: `ACTIVE` (PyTorch model & scaler verified).
3. Click **System Health** in the left sidebar:
   - Review the 4 infrastructure cards: FastAPI, Kafka KRaft, Neo4j, and C2GAT ML Checkpoint.
   - Click **Run Health Probes** to demonstrate sub-second live dependency checks.

### Minute 1:30 – 3:30 | Operational Overview & KPIs
1. Navigate to **Overview**:
   - **Total Processed**: 2,512 transactions across 495 unique customer accounts.
   - **Transaction Volume**: $747,555.57 USD.
   - **Flagged Volume**: 1,683 transactions (67.0% flagged based on rule score ≥ 50 or anomaly score ≥ 0.5).
   - **High-Risk Accounts**: 353 accounts exhibiting network sprawl or velocity bursts.
2. Point out the **Risk Tier Distribution Spectrum**:
   - Low: 79 transactions (3.1%)
   - Medium: 1,605 transactions (63.9%)
   - High: 724 transactions (28.8%)
   - Critical: 104 transactions (4.1%)

### Minute 3:30 – 5:30 | Real-Time Transaction Streaming
1. Navigate to **Live Transactions**.
2. Notice the real-time table displaying timestamp, TxID, Account, Amount, Risk Score, Anomaly %, and Status.
3. Open a second PowerShell terminal to simulate streaming live transactions:
   ```powershell
   python producer/transaction_producer.py --limit 10 --delay 0.5
   ```
4. Observe the frontend dashboard table:
   - As Kafka receives transactions, newly enriched events appear at the top of the table highlighted in cyan with a `NEW` badge.
   - Total records and KPI volume counters dynamically increment without a page reload.

### Minute 5:30 – 7:00 | Deep-Dive Transaction Investigation Drawer
1. In the transaction table, search for **`TX001635`** (or click **Inspect** on any Critical transaction).
2. The **Transaction Investigation Drawer** slides in from the right:
   - **Approach B Risk**: `100 / 100` (Critical tier).
   - **Approach A Score**: `61.5 / 100`.
   - **C2GAT Anomaly Score**: `68.5%` reconstruction outlier.
   - **Attribution Triggers**:
     - *Dense shared device*: 6 accounts (+25 pts)
     - *High transaction amount*: $1,762.28 (> $589.54) (+20 pts)
     - *Rapid velocity burst*: 1 other tx within 24h (+20 pts)
     - *High account network sprawl*: degree 24 (+10 pts)
3. Click **"Explore AC00358 Subgraph"** directly from the drawer.

### Minute 7:00 – 8:30 | Interactive Network Graph Explorer
1. The dashboard transitions to the **Network Graph** tab centered on account `AC00358`:
   - Blue Node: Account Anchor (`AC00358`).
   - Cyan Nodes: Executed Transactions.
   - Emerald Nodes: Shared Hardware Devices.
   - Amber Nodes: Shared IP Addresses.
   - Purple Nodes: Merchant Recipients.
2. Demonstrate graph interactivity:
   - Click on any connected Device or IP node to inspect its properties in the **Entity Inspector** panel.
   - Zoom in/out and drag the canvas to explore graph density.
   - Click quick-switch chips for known sprawling accounts (e.g. `AC00004`, `AC00128`, `AC00453`).

### Minute 8:30 – 10:00 | Model Comparison & Ground-Truth Disclaimer
1. Navigate to **Model Comparison**:
   - Contrast **Phase 5 Graph Rules** (interpretable, deterministic) with **Phase 6 C2GAT ML** (unsupervised time-aware graph attention autoencoder).
   - Review Pearson correlations ($r \approx 0.80$ between Approach A and B; $r \approx 0.38$ with C2GAT Anomaly).
2. Conclude with the **Scientific Interpretability Disclaimer**:
   - Emphasize that the system measures structural and temporal risk; it does not claim confirmed fraud without ground-truth labels.
   - High scores prompt human compliance review rather than automatic account freeze.

---

## 5. Verification Commands Reference

| Test Scope | Command | Expected Result |
| :--- | :--- | :--- |
| **All Automated Tests** | `python -m pytest backend/tests/test_api.py tests/test_e2e_pipeline.py -v` | 17 Passed |
| **End-to-End Pipeline** | `python -m pytest tests/test_e2e_pipeline.py -v` | 5 Passed |
| **Backend Unit Tests** | `python -m pytest backend/tests/test_api.py -v` | 12 Passed |
| **Phase 6 ML Verification** | `python ml/verify_phase6.py` | 42/42 Passed |
| **Phase 5 Risk Scoring** | `python neo4j/verify_risk_scoring.py` | All Passed |
| **Phase 1 Validation** | `python data/validate_data.py` | 2,512 Rows Clean |
| **Frontend Production Build** | `cd frontend/fraud-dashboard; npm run build` | Built in ~15s (0 errors) |

---

## 6. Troubleshooting Common Issues

1. **Port 8000 or 5173 already in use:**
   ```powershell
   Get-NetTCPConnection -LocalPort 8000, 5173 -State Listen
   ```
   Run `.\scripts\stop_all.ps1` to cleanly release ports before restarting.

2. **Kafka segment locking on Windows:**
   Kafka KRaft server properties are configured with `log.cleaner.enable=false` and `log.retention.hours=87600` to prevent Windows memory-mapped file locking conflicts.
