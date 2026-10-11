# Graph-Based Transaction Risk Scoring Design

## Overview
This document specifies the design of a transparent, graph-derived risk scoring system for the streaming fraud detection pipeline. The analysis is derived empirically from the complete 2,512 transactions, 495 accounts, 681 devices, 592 IP addresses, and 100 merchants loaded into Neo4j.

> [!IMPORTANT]
> **No Ground-Truth Fraud Labels**: This dataset contains behavioral and topological transaction attributes but lacks verified fraud labels. The indicators analyzed herein represent structural anomalies and elevated operational risk patterns, **not** definitive proof of fraudulent intent.

---

## 1. Feature Definitions

We define six core graph- and transaction-level features corresponding to the Phase 5 graph patterns:

| Feature Name | Level | Graph Pattern / Concept | Description |
| :--- | :--- | :--- | :--- |
| **Shared Device** | Transaction / Entity | `(Account)-[:ACCESSED_VIA]->(Device)<-[:ACCESSED_VIA]-(Account)` | Number of distinct user accounts associated with the device used in the transaction. |
| **Shared IP** | Transaction / Entity | `(Account)-[:CONNECTED_FROM]->(IP)<-[:CONNECTED_FROM]-(Account)` | Number of distinct user accounts associated with the IP address originating the transaction. |
| **Merchant Cluster Size** | Transaction / Merchant | `(Account)-[:PERFORMED]->(:Transaction)-[:PAID_TO]->(Merchant)` | Total distinct accounts transacting with the recipient merchant. |
| **Transaction Amount** | Transaction | `Transaction.transaction_amount` | Numerical monetary value ($) of the transaction. |
| **Rapid Velocity** | Transaction / Account | `(Account)-[:PERFORMED]->(t1), (Account)-[:PERFORMED]->(t2)` | Number of other transactions executed by the same account within a 24-hour window ($\le 86,400\text{ s}$). |
| **Network Sprawl (Degree)** | Account | `Count(Distinct Device) + Count(Distinct IP) + Count(Distinct Merchant)` | Total distinct entity degree per account, measuring topological dispersion across devices, IPs, and merchants. |

---

## 2. Distribution Statistics

Empirical distributions computed across the complete population of **2,512 transactions** and **495 accounts** in Neo4j:

### 2.1 Transaction-Level Distributions ($N = 2,512$)

| Feature | Min | Max | Mean | Median (p50) | p75 | p90 | p95 | p99 | Std Dev |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Shared Device** (Accounts/Device) | 1.00 | 9.00 | 4.54 | 4.00 | 6.00 | 7.00 | 8.00 | 9.00 | 1.82 |
| **Shared IP** (Accounts/IP) | 1.00 | 13.00 | 5.13 | 5.00 | 6.00 | 8.00 | 9.00 | 10.00 | 2.04 |
| **Merchant Cluster** (Accounts/Merchant) | 13.00 | 44.00 | 25.42 | 25.00 | 28.00 | 31.00 | 32.00 | 44.00 | 4.96 |
| **Transaction Amount** ($) | $0.26 | $1,919.11 | $297.59 | $211.14 | $414.53 | $701.31 | $878.18 | $1,360.60 | $291.95 |
| **Rapid Velocity** (24h Tx Count) | 0.00 | 2.00 | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.21 |
| **Network Sprawl** (Account Degree) | 3.00 | 36.00 | 18.08 | 18.00 | 23.00 | 27.00 | 29.00 | 35.00 | 6.61 |

### 2.2 Account-Level Distributions ($N = 495$)

| Feature | Min | Max | Mean | Median (p50) | p75 | p90 | p95 | p99 | Std Dev |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Devices per Account** | 1.0 | 12.0 | 5.05 | 5.0 | 7.0 | 8.0 | 9.0 | 11.0 | 2.28 |
| **IPs per Account** | 1.0 | 12.0 | 5.05 | 5.0 | 7.0 | 8.0 | 9.0 | 11.0 | 2.27 |
| **Merchants per Account** | 1.0 | 12.0 | 4.94 | 5.0 | 6.0 | 8.0 | 9.0 | 11.0 | 2.22 |
| **Transactions per Account** | 1.0 | 12.0 | 5.07 | 5.0 | 7.0 | 8.0 | 9.0 | 11.0 | 2.29 |
| **Total Entity Degree per Account** | 3.0 | 36.0 | 15.04 | 15.0 | 20.0 | 24.0 | 27.0 | 33.0 | 6.74 |

### 2.3 Affected Entity Counts

| Indicator Trigger Threshold | Affected Transactions | % of Total Transactions | Unique Accounts Affected | % of Total Accounts |
| :--- | :---: | :---: | :---: | :---: |
| **Shared Device** ($> 1$ account) | 2,440 | 97.13% | 493 | 99.60% |
| **Shared Device (Heavy)** ($\ge 7$ accounts, $\ge \text{p90}$) | 344 | 13.69% | 237 | 47.88% |
| **Shared IP** ($> 1$ account) | 2,472 | 98.41% | 495 | 100.00% |
| **Shared IP (Heavy)** ($\ge 8$ accounts, $\ge \text{p90}$) | 360 | 14.33% | 243 | 49.09% |
| **Merchant Cluster** ($> 1$ account) | 2,512 | 100.00% | 495 | 100.00% |
| **Merchant Cluster (Heavy)** ($\ge 31$ accounts, $\ge \text{p90}$) | 358 | 14.25% | 275 | 55.56% |
| **High Value** ($> \mu + 1\sigma = \$589.54$) | 354 | 14.09% | 252 | 50.91% |
| **Rapid Velocity** ($\ge 1$ tx within 24h) | 100 | 3.98% | 49 | 9.90% |
| **Network Sprawl (High)** ($\text{degree} > \text{p75} = 23$) | 563 | 22.41% | 62 | 12.53% |

---

## 3. Normalization Formulas

Each feature $x$ is mapped to a normalized score $S(x) \in [0, 1]$ to allow equitable comparison across disparate units (counts, dollars, entity degrees).

### 3.1 `shared_device_score` ($S_{\text{dev}}$)
Measures device sharing intensity. Minimum sharing is 1 account (unshared). Capped at empirical max of 9.
$$S_{\text{dev}} = \text{clip}\left(\frac{\text{accounts\_per\_device} - 1}{9 - 1}, 0.0, 1.0\right)$$

### 3.2 `shared_ip_score` ($S_{\text{ip}}$)
Measures IP sharing intensity. Minimum is 1 account (isolated). Capped at empirical max of 13.
$$S_{\text{ip}} = \text{clip}\left(\frac{\text{accounts\_per\_ip} - 1}{13 - 1}, 0.0, 1.0\right)$$

### 3.3 `merchant_cluster_score` ($S_{\text{merch}}$)
Reflects relative merchant concentration within the empirical merchant support $[13, 44]$.
$$S_{\text{merch}} = \text{clip}\left(\frac{\text{accounts\_per\_merchant} - 13}{44 - 13}, 0.0, 1.0\right)$$

### 3.4 `amount_score` ($S_{\text{amt}}$)
Measures monetary exposure. Since amount has a long-tailed positive skew (mean $\$297.59$, max $\$1,919.11$, 99th percentile $\$1,360.60$), a soft cap at $\$1,000.00$ provides strong separation:
$$S_{\text{amt}} = \text{clip}\left(\frac{\text{transaction\_amount}}{1000.0}, 0.0, 1.0\right)$$

### 3.5 `velocity_score` ($S_{\text{vel}}$)
Measures high-frequency transaction repetition by the same account within 24 hours. The observed maximum velocity count is 2.
$$S_{\text{vel}} = \text{clip}\left(\frac{\text{tx\_within\_24h\_count}}{2.0}, 0.0, 1.0\right)$$

### 3.6 `network_sprawl_score` ($S_{\text{sprawl}}$)
Measures topological entity dispersion across devices, IPs, and merchants $[3, 36]$.
$$S_{\text{sprawl}} = \text{clip}\left(\frac{\text{total\_entity\_degree} - 3}{36 - 3}, 0.0, 1.0\right)$$

---

## 4. Indicator Overlap and Correlation Analysis

### 4.1 Transaction Indicator Trigger Count

Evaluating the 5 core discriminating indicators (**Shared Device**, **Shared IP**, **High Value**, **Rapid Velocity**, **Network Sprawl**):

| Number of Triggered Indicators | Number of Transactions | Percentage | Cumulative |
| :---: | :---: | :---: | :---: |
| **0 Indicators** | 0 | 0.00% | 0.00% |
| **1 Indicator** | 74 | 2.95% | 2.95% |
| **2 Indicators** | 1,583 | 63.02% | 65.96% |
| **3 Indicators** | 738 | 29.38% | 95.34% |
| **4 Indicators** | 110 | 4.38% | 99.72% |
| **5 Indicators** | 7 | 0.28% | 100.00% |
| **4+ Indicators** | **117** | **4.66%** | — |

### 4.2 Account Indicator Trigger Count ($N = 495$)

| Number of Triggered Indicators | Number of Accounts | Percentage |
| :---: | :---: | :---: |
| **0 Indicators** | 0 | 0.00% |
| **1 Indicator** | 2 | 0.40% |
| **2 Indicators** | 203 | 41.01% |
| **3 Indicators** | 190 | 38.38% |
| **4 Indicators** | 79 | 15.96% |
| **5 Indicators** | 21 | 4.24% |
| **4+ Indicators** | **100** | **20.20%** |

### 4.3 Key Pairwise Intersections

| Indicator Combination | Affected Transactions | % of Total Transactions | Accounts Involved |
| :--- | :---: | :---: | :---: |
| **Shared Device + Shared IP** | 2,401 | 95.58% | 493 |
| **Shared Device + Rapid Velocity** | 97 | 3.86% | 49 |
| **Shared IP + Rapid Velocity** | 99 | 3.94% | 49 |
| **High Value + Rapid Velocity** | 18 | 0.72% | 35 |
| **Shared Device + High Value** | 349 | 13.89% | 252 |
| **Shared IP + High Value** | 348 | 13.85% | 252 |
| **Multi-Entity Sprawl + High Value** | 81 | 3.22% | 51 |
| **Shared Dev + Shared IP + Velocity** | 96 | 3.82% | 49 |
| **Shared Dev + Shared IP + High Val + Velocity** | 17 | 0.68% | 35 |

> [!NOTE]
> **Observation on Prevalence**: Because 97.1% and 98.4% of transactions exhibit binary device and IP sharing respectively, simple binary sharing is an **ambient baseline property** of this graph rather than an acute risk signal. In contrast, the joint occurrence of **High Value + Rapid Velocity** (18 transactions, 0.72%) or **All Four Combined** (17 transactions, 0.68%) isolates highly concentrated topological anomalies.

---

## 5. Scoring Approaches

### Approach A: Equal-Weight Normalized Composite Score
A continuous, compensatory multi-factor model mapping normalized indicators into a 0–100 scale:

$$\text{RiskScore}_A = \frac{100}{6} \left( S_{\text{dev}} + S_{\text{ip}} + S_{\text{merch}} + S_{\text{amt}} + S_{\text{vel}} + S_{\text{sprawl}} \right)$$

* **Empirical Score Distribution ($N = 2,512$)**:
  * Min: $9.14$
  * Max: $62.57$
  * Mean: $32.57$
  * Median: $32.03$
  * p75: $37.77$
  * p90: $43.37$
  * p95: $46.45$
  * p99: $53.46$
  * Std Dev: $8.01$

---

### Approach B: Rule-Based Additive Points
A non-compensatory point-allocation system where specific structural thresholds accrue discrete penalty points:

| Rule Condition | Points Contributed | Rationale |
| :--- | :---: | :--- |
| **Shared Device (Base)**: $> 1$ account | +15 pts | Base device multi-tenancy |
| **Shared Device (Heavy)**: $\ge 6$ accounts | +10 pts bonus | Top 25% dense device sharing |
| **Shared IP (Base)**: $> 1$ account | +15 pts | Base network multi-tenancy |
| **Shared IP (Heavy)**: $\ge 8$ accounts | +10 pts bonus | Top 10% dense IP sharing |
| **Merchant Concentration**: $\ge 30$ accounts | +10 pts | High-density merchant cluster |
| **High Value Transaction**: $> \$589.54$ | +20 pts | Monetary exposure exceeds $\mu + 1\sigma$ |
| **Rapid Transaction Velocity**: $\ge 1$ tx within 24h | +20 pts | High-frequency burst activity |
| **High Network Sprawl**: Degree $> 23$ | +10 pts | Account entity dispersion in top quartile |
| **Total Possible** | **110 pts** (Capped at 100) | |

* **Empirical Score Distribution ($N = 2,512$)**:
  * Min: $10.0$
  * Max: $100.0$
  * Mean: $41.58$
  * Median: $40.0$
  * p75: $50.0$
  * p90: $60.0$
  * p95: $60.0$
  * p99: $70.0$
  * Std Dev: $12.06$

---

## 6. Comparison of Scoring Approaches

| Evaluation Criteria | Approach A: Equal-Weight Normalized | Approach B: Rule-Based Additive |
| :--- | :--- | :--- |
| **Interpretability** | Moderate: Yields a smooth continuous value; explaining why a score is 37.2 requires inspecting continuous sub-fractions. | High: Clear breakdown (e.g., "Flagged +20 for high value, +20 for velocity, +15 for shared IP = 55"). |
| **Sensitivity** | Linear/Smooth: Reflects incremental variations across all six dimensions simultaneously. | Discrete/Step-wise: Sensitive only when specific thresholds are breached; insensitive to sub-threshold drift. |
| **Data Requirements** | Requires continuous distribution parameters ($\min, \max, \text{percentiles}$) to compute normalizations accurately. | Requires discrete cutoff boundaries (e.g., $\$589.54$, $\ge 6$ accounts, $\le 24\text{h}$). |
| **Susceptibility to False Positives** | Low variance in extremes; high clustering around the mean ($32.57 \pm 8.01$), making thresholding subtle. | Higher tail dispersion; ambient shared device/IP guarantees $\ge 30$ base points for most transactions. |
| **Ease of Implementation** | Straightforward in Python / Cypher using mathematical division and clamping functions. | Straightforward in SQL / Cypher / Python using `CASE WHEN` conditional point increments. |

---

## 7. Data Limitations & Operational Realities

1. **Absence of Ground-Truth Fraud Labels**:
   * The dataset does not contain an authoritative `is_fraud` ground truth column. No scoring mechanism can claim verified classification accuracy (e.g., Precision, Recall, AUC-ROC) without an established validation dataset.
2. **Behavioral and Structural vs. Malicious Intent**:
   * Graph indicators model topological patterns. A device or IP shared across accounts frequently reflects legitimate environments: shared family computers, corporate gateways, universities, airport Wi-Fi, or VPN services.
3. **High Monetary Value $\ne$ Fraud**:
   * Legitimate users frequently conduct high-value purchases. Monetary amount reflects financial exposure, not behavioral criminality.
4. **Velocity in Everyday Commerce**:
   * Sub-24-hour multiple transactions often reflect normal consumer purchasing runs (e.g., buying groceries followed by fuel or retail purchases).
5. **Synthetic Graph Artifacts**:
   * In this dataset, all 100 merchants are shared by between 13 and 44 accounts, and $>97\%$ of transactions involve shared devices/IPs. A binary "shared" check without percentile thresholds has low discriminating value on this specific graph topology.

---

## 8. Recommended Next Steps

Without making subjective policy choices, the logical subsequent engineering phases are:
1. **Dynamic Risk Metric Enrichment**: Implement Cypher queries or a lightweight computation module to write calculated risk scores and pattern triggers directly onto `(:Transaction)` nodes as node properties (`risk_score_a`, `risk_score_b`, `risk_flags`).
2. **API Endpoint Integration**: Build read-only REST endpoints in `backend/main.py` exposing transaction risk profiles and graph subgraphs for visual inspection.
3. **Investigator Dashboard**: Display transactions with ranked risk scores, drill-down explanations of triggered rules, and interactive graph neighborhood visualizations.
