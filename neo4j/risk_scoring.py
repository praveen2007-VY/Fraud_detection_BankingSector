"""
Fraud Detection System — Graph-Based Transaction Risk Scoring Engine
File: neo4j/risk_scoring.py

Implements:
1. Feature extraction from Neo4j graph nodes and relationships.
2. Approach A: Equal-Weight Normalized Composite Score (0–100).
3. Approach B: Rule-Based Additive Point System (0–100).
4. Explainable indicator attribution and human-readable risk reason logging.
"""

import os
import sys
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Ensure UTF-8 output on Windows console
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
load_dotenv()


class RiskScoringEngine:
    """
    Computes graph-derived risk scores for transactions based on Neo4j topology.
    """

    # Normalization parameters established in neo4j/risk_scoring_design.md
    DEVICE_MIN = 1.0
    DEVICE_MAX = 9.0

    IP_MIN = 1.0
    IP_MAX = 13.0

    MERCHANT_MIN = 13.0
    MERCHANT_MAX = 44.0

    AMOUNT_SOFT_CAP = 1000.0
    VELOCITY_CAP = 2.0

    DEGREE_MIN = 3.0
    DEGREE_MAX = 36.0

    # Approach B threshold cutoffs
    HIGH_VALUE_THRESHOLD = 589.54   # mean ($253.28) + 1*std ($336.26)
    HEAVY_DEVICE_THRESHOLD = 6      # >= 6 accounts (top ~25%)
    HEAVY_IP_THRESHOLD = 8          # >= 8 accounts (top ~10%)
    HEAVY_MERCHANT_THRESHOLD = 30   # >= 30 accounts (~p90)
    HIGH_SPRAWL_THRESHOLD = 23      # degree > 23 (p75)

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "fraud_detection_2026")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self.driver:
            self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def fetch_transaction_graph_features(self) -> pd.DataFrame:
        """
        Queries Neo4j for all transactions, their linked entities, and graph degrees.
        """
        query_tx = """
        MATCH (a:Account)-[:PERFORMED]->(t:Transaction)
        OPTIONAL MATCH (t)-[:USED_DEVICE]->(d:Device)
        OPTIONAL MATCH (t)-[:ORIGINATED_FROM]->(i:IP)
        OPTIONAL MATCH (t)-[:PAID_TO]->(m:Merchant)
        
        CALL (d) {
            MATCH (a2:Account)-[:ACCESSED_VIA]->(d)
            RETURN count(DISTINCT a2) AS device_accounts_count
        }
        CALL (i) {
            MATCH (a3:Account)-[:CONNECTED_FROM]->(i)
            RETURN count(DISTINCT a3) AS ip_accounts_count
        }
        CALL (m) {
            MATCH (a4:Account)-[:PERFORMED]->(:Transaction)-[:PAID_TO]->(m)
            RETURN count(DISTINCT a4) AS merchant_accounts_count
        }
        
        RETURN t.transaction_id AS transaction_id,
               a.account_id AS account_id,
               t.transaction_amount AS transaction_amount,
               t.transaction_date AS transaction_date,
               d.device_id AS device_id,
               device_accounts_count,
               i.ip_address AS ip_address,
               ip_accounts_count,
               m.merchant_id AS merchant_id,
               merchant_accounts_count
        ORDER BY t.transaction_id ASC
        """

        query_account_sprawl = """
        MATCH (a:Account)
        OPTIONAL MATCH (a)-[:ACCESSED_VIA]->(d:Device)
        OPTIONAL MATCH (a)-[:CONNECTED_FROM]->(i:IP)
        OPTIONAL MATCH (a)-[:PERFORMED]->(t:Transaction)-[:PAID_TO]->(m:Merchant)
        WITH a,
             count(DISTINCT d) AS device_count,
             count(DISTINCT i) AS ip_count,
             count(DISTINCT m) AS merchant_count,
             count(DISTINCT t) AS transaction_count
        RETURN a.account_id AS account_id,
               device_count,
               ip_count,
               merchant_count,
               transaction_count,
               (device_count + ip_count + merchant_count) AS total_entity_degree
        """

        with self.driver.session() as session:
            tx_records = session.run(query_tx).data()
            acc_records = session.run(query_account_sprawl).data()

        df_tx = pd.DataFrame(tx_records)
        df_acc = pd.DataFrame(acc_records)

        # Merge account entity degree
        df = df_tx.merge(df_acc[['account_id', 'total_entity_degree']], on='account_id', how='left')

        # Compute rapid velocity (other transactions by same account within 24 hours / 86400s)
        df['dt'] = pd.to_datetime(df['transaction_date'])
        df = df.sort_values(by=['account_id', 'dt']).reset_index(drop=True)

        velocity_counts = []
        for _, row in df.iterrows():
            acct = row['account_id']
            t_time = row['dt']
            acct_txs = df[df['account_id'] == acct]
            diffs = (acct_txs['dt'] - t_time).abs().dt.total_seconds()
            other_diffs = diffs[diffs > 0]
            within_24h = int((other_diffs <= 86400).sum())
            velocity_counts.append(within_24h)

        df['velocity_24h_count'] = velocity_counts
        # Sort back to transaction_id order
        df = df.sort_values(by='transaction_id').reset_index(drop=True)
        return df

    def compute_approach_a(self, row: pd.Series) -> Dict[str, Any]:
        """
        Calculates Approach A: Equal-Weight Normalized Composite Score (0–100).
        """
        # Normalizations
        s_dev = np.clip((row['device_accounts_count'] - self.DEVICE_MIN) / (self.DEVICE_MAX - self.DEVICE_MIN), 0.0, 1.0)
        s_ip = np.clip((row['ip_accounts_count'] - self.IP_MIN) / (self.IP_MAX - self.IP_MIN), 0.0, 1.0)
        s_merch = np.clip((row['merchant_accounts_count'] - self.MERCHANT_MIN) / (self.MERCHANT_MAX - self.MERCHANT_MIN), 0.0, 1.0)
        s_amt = np.clip(row['transaction_amount'] / self.AMOUNT_SOFT_CAP, 0.0, 1.0)
        s_vel = np.clip(row['velocity_24h_count'] / self.VELOCITY_CAP, 0.0, 1.0)
        s_sprawl = np.clip((row['total_entity_degree'] - self.DEGREE_MIN) / (self.DEGREE_MAX - self.DEGREE_MIN), 0.0, 1.0)

        raw_sum = s_dev + s_ip + s_merch + s_amt + s_vel + s_sprawl
        score = float(np.round((100.0 / 6.0) * raw_sum, 2))

        # Attribution / top contributors (score >= 0.5 or high relative contribution)
        contributions = {
            "Shared Device": s_dev,
            "Shared IP": s_ip,
            "Merchant Concentration": s_merch,
            "Transaction Amount": s_amt,
            "Transaction Velocity": s_vel,
            "Network Sprawl": s_sprawl
        }
        prominent = [name for name, val in contributions.items() if val >= 0.50]

        return {
            "approach_a_score": score,
            "s_dev": round(float(s_dev), 4),
            "s_ip": round(float(s_ip), 4),
            "s_merch": round(float(s_merch), 4),
            "s_amt": round(float(s_amt), 4),
            "s_vel": round(float(s_vel), 4),
            "s_sprawl": round(float(s_sprawl), 4),
            "approach_a_prominent": prominent
        }

    def compute_approach_b(self, row: pd.Series) -> Dict[str, Any]:
        """
        Calculates Approach B: Rule-Based Additive Points (0–100).
        """
        pts_dev = 0
        dev_reason = None
        if row['device_accounts_count'] >= self.HEAVY_DEVICE_THRESHOLD:
            pts_dev = 25
            dev_reason = f"Dense shared device: {int(row['device_accounts_count'])} accounts (+25 pts)"
        elif row['device_accounts_count'] > 1:
            pts_dev = 15
            dev_reason = f"Shared device: {int(row['device_accounts_count'])} accounts (+15 pts)"

        pts_ip = 0
        ip_reason = None
        if row['ip_accounts_count'] >= self.HEAVY_IP_THRESHOLD:
            pts_ip = 25
            ip_reason = f"Dense shared IP: {int(row['ip_accounts_count'])} accounts (+25 pts)"
        elif row['ip_accounts_count'] > 1:
            pts_ip = 15
            ip_reason = f"Shared IP: {int(row['ip_accounts_count'])} accounts (+15 pts)"

        pts_merch = 0
        merch_reason = None
        if row['merchant_accounts_count'] >= self.HEAVY_MERCHANT_THRESHOLD:
            pts_merch = 10
            merch_reason = f"Dense merchant cluster: {int(row['merchant_accounts_count'])} accounts (+10 pts)"

        pts_amt = 0
        amt_reason = None
        if row['transaction_amount'] > self.HIGH_VALUE_THRESHOLD:
            pts_amt = 20
            amt_reason = f"High transaction amount: ${row['transaction_amount']:.2f} (> ${self.HIGH_VALUE_THRESHOLD:.2f}) (+20 pts)"

        pts_vel = 0
        vel_reason = None
        if row['velocity_24h_count'] >= 1:
            pts_vel = 20
            vel_reason = f"Rapid velocity burst: {int(row['velocity_24h_count'])} tx within 24h (+20 pts)"

        pts_sprawl = 0
        sprawl_reason = None
        if row['total_entity_degree'] > self.HIGH_SPRAWL_THRESHOLD:
            pts_sprawl = 10
            sprawl_reason = f"High account network sprawl: degree {int(row['total_entity_degree'])} (+10 pts)"

        total_pts = min(100, pts_dev + pts_ip + pts_merch + pts_amt + pts_vel + pts_sprawl)

        reasons = [r for r in [dev_reason, ip_reason, merch_reason, amt_reason, vel_reason, sprawl_reason] if r is not None]

        return {
            "approach_b_score": total_pts,
            "pts_dev": pts_dev,
            "pts_ip": pts_ip,
            "pts_merch": pts_merch,
            "pts_amt": pts_amt,
            "pts_vel": pts_vel,
            "pts_sprawl": pts_sprawl,
            "approach_b_reasons": reasons
        }

    def score_all_transactions(self) -> pd.DataFrame:
        """
        Executes end-to-end scoring pipeline and returns comprehensive DataFrame.
        """
        df = self.fetch_transaction_graph_features()

        records = []
        for _, row in df.iterrows():
            res_a = self.compute_approach_a(row)
            res_b = self.compute_approach_b(row)

            # Combined human-readable explanation
            all_reasons = []
            if res_b["approach_b_reasons"]:
                all_reasons.extend(res_b["approach_b_reasons"])
            else:
                all_reasons.append("Baseline activity (no rule thresholds triggered)")

            rec = {
                "transaction_id": row["transaction_id"],
                "account_id": row["account_id"],
                "transaction_amount": float(row["transaction_amount"]),
                "transaction_date": row["transaction_date"],
                "device_id": row["device_id"],
                "shared_device_accounts": int(row["device_accounts_count"]),
                "ip_address": row["ip_address"],
                "shared_ip_accounts": int(row["ip_accounts_count"]),
                "merchant_id": row["merchant_id"],
                "merchant_cluster_accounts": int(row["merchant_accounts_count"]),
                "rapid_velocity_count_24h": int(row["velocity_24h_count"]),
                "account_network_sprawl_degree": int(row["total_entity_degree"]),
                "approach_a_score": res_a["approach_a_score"],
                "approach_b_score": res_b["approach_b_score"],
                "risk_reasons": "; ".join(all_reasons),
                "approach_a_prominent_factors": ", ".join(res_a["approach_a_prominent"]) if res_a["approach_a_prominent"] else "None (Balanced)"
            }
            records.append(rec)

        return pd.DataFrame(records)


def main():
    with RiskScoringEngine() as engine:
        print("Extracting features and scoring transactions...")
        df_scored = engine.score_all_transactions()
        print(f"Scored {len(df_scored)} transactions successfully.")
        print(df_scored.head(5).to_string())


if __name__ == "__main__":
    main()
