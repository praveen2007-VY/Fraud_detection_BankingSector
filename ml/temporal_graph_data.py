"""
Fraud Detection System — Phase 6
File: ml/temporal_graph_data.py

Purpose:
    Build the temporal transaction graph dataset for C2GAT-inspired training.
    - Constructs directed temporal edges between transactions sharing entities
    - Extracts temporal features from TransactionDate
    - Assembles the final dataset with neighbors for each transaction

CRITICAL CONSTRAINTS:
    - Uses ONLY real data from data/transactions_clean.csv and ml/features_unsupervised.csv
    - NO synthetic transactions
    - NO fraud labels
    - Temporal ordering is strictly preserved (no future leakage)
    - PreviousTransactionDate is EXCLUDED (found to be futuristic/synthetic)
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SEED = 42
np.random.seed(SEED)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLEAN_CSV = os.path.join(PROJECT_ROOT, "data", "transactions_clean.csv")
FEATURES_CSV = os.path.join(PROJECT_ROOT, "ml", "features_unsupervised.csv")
SCORED_CSV = os.path.join(PROJECT_ROOT, "neo4j", "scored_transactions.csv")

ML_FEATURE_COLS = [
    "transaction_amount",
    "transaction_duration",
    "login_attempts",
    "customer_age",
    "account_balance",
    "amount_to_balance_ratio",
    "shared_device_accounts",
    "shared_ip_accounts",
    "merchant_cluster_accounts",
    "rapid_velocity_count_24h",
    "account_network_sprawl_degree",
    "is_credit",
    "channel_atm",
    "channel_online",
    "channel_branch",
]

K_NEIGHBORS = 10  # Maximum temporal neighbors per transaction


def load_and_merge_data() -> pd.DataFrame:
    """
    Load clean transactions and feature matrix, merge into one frame.
    Returns the merged DataFrame sorted chronologically.
    """
    df_clean = pd.read_csv(CLEAN_CSV)
    df_feat = pd.read_csv(FEATURES_CSV)
    df_scored = pd.read_csv(SCORED_CSV)

    assert len(df_clean) == 2512, f"Expected 2512 clean rows, got {len(df_clean)}"
    assert len(df_feat) == 2512, f"Expected 2512 feature rows, got {len(df_feat)}"
    assert len(df_scored) == 2512, f"Expected 2512 scored rows, got {len(df_scored)}"

    # Parse real transaction timestamps
    df_clean["timestamp"] = pd.to_datetime(df_clean["TransactionDate"])

    # Merge: clean tx metadata + ML features
    merged = df_clean[["TransactionID", "AccountID", "DeviceID", "IP Address",
                        "MerchantID", "timestamp"]].rename(columns={
        "TransactionID": "transaction_id",
        "AccountID": "account_id",
        "DeviceID": "device_id",
        "IP Address": "ip_address",
        "MerchantID": "merchant_id",
    })

    # Add ML features
    merged = merged.merge(df_feat, on="transaction_id", how="inner")
    assert len(merged) == 2512, f"Merge mismatch: {len(merged)}"

    # Add Phase-5 scores (reference only — NOT used as training labels)
    scored_slim = df_scored[["transaction_id", "approach_a_score", "approach_b_score",
                              "risk_reasons", "approach_a_prominent_factors"]]
    merged = merged.merge(scored_slim, on="transaction_id", how="left")
    assert len(merged) == 2512, f"Merge mismatch after scores: {len(merged)}"

    # CRITICAL: Sort chronologically — temporal graph requires this
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged["chrono_idx"] = merged.index  # chronological position

    return merged


def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all derived temporal features from real TransactionDate timestamps.

    Features:
        t_norm              : Normalized position in time window [0,1]
        day_of_week         : Day of week, normalized [0,1]
        hour_of_day         : Hour of day, normalized [0,1]
        month_of_year       : Month, normalized [0,1]
        inter_tx_gap_norm   : Log-normalized time gap since previous same-account tx
        rolling_tx_count_7d : Count of same-account tx within ±7 days

    NOTE: PreviousTransactionDate is EXCLUDED — values are in 2024-11-04 range,
    which is beyond the transaction range (2023-01-02 to 2024-01-01). This
    strongly suggests the column is synthetic / placeholder data.
    """
    df = df.copy()
    t_min = df["timestamp"].min()
    t_max = df["timestamp"].max()
    total_seconds = (t_max - t_min).total_seconds()

    df["t_norm"] = ((df["timestamp"] - t_min).dt.total_seconds() / total_seconds).round(8)
    df["day_of_week"] = (df["timestamp"].dt.dayofweek / 6.0).round(6)
    df["hour_of_day"] = (df["timestamp"].dt.hour / 23.0).round(6)
    df["month_of_year"] = ((df["timestamp"].dt.month - 1) / 11.0).round(6)

    # Inter-transaction gap: time since previous transaction of the same account
    df_sorted = df.sort_values(["account_id_x", "timestamp"]).copy()
    df_sorted["prev_ts"] = df_sorted.groupby("account_id_x")["timestamp"].shift(1)
    df_sorted["gap_seconds"] = (
        df_sorted["timestamp"] - df_sorted["prev_ts"]
    ).dt.total_seconds().fillna(0.0).clip(lower=0.0)

    max_gap = df_sorted["gap_seconds"].max()
    df_sorted["inter_tx_gap_norm"] = (
        np.log1p(df_sorted["gap_seconds"]) / np.log1p(max_gap + 1e-9)
    ).round(8)

    # Rolling 7-day transaction count for same account
    # Efficient implementation: for each transaction, count same-account tx within 7 days
    seven_days_sec = 7 * 24 * 3600
    rolling_counts = []
    for i, row in df_sorted.iterrows():
        acct = row["account_id_x"]
        t_cur = row["timestamp"]
        acct_mask = df_sorted["account_id_x"] == acct
        t_diffs = (df_sorted.loc[acct_mask, "timestamp"] - t_cur).dt.total_seconds().abs()
        count_7d = int((t_diffs <= seven_days_sec).sum()) - 1  # exclude self
        rolling_counts.append(max(0, count_7d))
    df_sorted["rolling_tx_count_7d"] = rolling_counts

    # Merge temporal features back to original order
    temporal_cols = ["transaction_id", "inter_tx_gap_norm", "rolling_tx_count_7d",
                     "gap_seconds"]
    df = df.merge(df_sorted[temporal_cols], on="transaction_id", how="left")

    # Copy scalars
    df["t_norm"] = df_sorted["t_norm"].values
    df["day_of_week"] = df_sorted["day_of_week"].values
    df["hour_of_day"] = df_sorted["hour_of_day"].values
    df["month_of_year"] = df_sorted["month_of_year"].values
    df["inter_tx_gap_norm"] = df_sorted["inter_tx_gap_norm"].values
    df["rolling_tx_count_7d"] = df_sorted["rolling_tx_count_7d"].values

    return df


def build_temporal_graph(df: pd.DataFrame, k: int = K_NEIGHBORS) -> Dict:
    """
    Build temporal transaction graph.

    Nodes: each transaction (indexed 0..N-1 in chronological order)
    Edges: directed from earlier to later transaction, when they share any of:
        - Same AccountID (SAME_ACCOUNT)
        - Same DeviceID  (SAME_DEVICE)
        - Same IP Address (SAME_IP)
        - Same MerchantID (SAME_MERCHANT)

    For each transaction i, we record its k most recent predecessors.

    TEMPORAL CONSTRAINT: Edge j -> i exists ONLY IF t_j < t_i
    This ensures no future leakage.

    Returns:
        graph_data: dict with keys:
            'nodes': N transaction dicts
            'neighbors': list of lists, neighbors[i] = [j1, j2, ..., jk] (indices, chrono sorted desc)
            'edge_types': list of lists, edge_types[i] = [type_j1, ...]
            'n_nodes': total node count
            'n_edges': total edge count
    """
    n = len(df)

    # Build lookup indices for fast entity matching
    # account -> list of chrono indices
    acct_to_idx: Dict[str, List[int]] = {}
    dev_to_idx: Dict[str, List[int]] = {}
    ip_to_idx: Dict[str, List[int]] = {}
    merchant_to_idx: Dict[str, List[int]] = {}

    for i, row in df.iterrows():
        acct = row["account_id_x"]
        dev = row["device_id"]
        ip = row["ip_address"]
        merch = row["merchant_id"]

        acct_to_idx.setdefault(acct, []).append(i)
        dev_to_idx.setdefault(dev, []).append(i)
        ip_to_idx.setdefault(ip, []).append(i)
        merchant_to_idx.setdefault(merch, []).append(i)

    all_neighbors = []
    all_edge_types = []
    total_edges = 0

    for i in range(n):
        row = df.iloc[i]
        acct = row["account_id_x"]
        dev = row["device_id"]
        ip = row["ip_address"]
        merch = row["merchant_id"]

        # Collect candidate predecessors with edge type
        candidates: Dict[int, str] = {}  # idx -> edge_type (priority: account > device > ip > merchant)

        for j in acct_to_idx.get(acct, []):
            if j < i:
                candidates[j] = "SAME_ACCOUNT"

        for j in dev_to_idx.get(dev, []):
            if j < i and j not in candidates:
                candidates[j] = "SAME_DEVICE"

        for j in ip_to_idx.get(ip, []):
            if j < i and j not in candidates:
                candidates[j] = "SAME_IP"

        for j in merchant_to_idx.get(merch, []):
            if j < i and j not in candidates:
                candidates[j] = "SAME_MERCHANT"

        # Sort by recency (descending) and take top k
        sorted_candidates = sorted(candidates.keys(), reverse=True)[:k]
        neighbor_types = [candidates[j] for j in sorted_candidates]

        all_neighbors.append(sorted_candidates)
        all_edge_types.append(neighbor_types)
        total_edges += len(sorted_candidates)

    return {
        "nodes": df,
        "neighbors": all_neighbors,
        "edge_types": all_edge_types,
        "n_nodes": n,
        "n_edges": total_edges,
        "k": k,
    }


def get_temporal_feature_cols() -> List[str]:
    """Return the list of temporal feature column names added in Phase 6."""
    return ["t_norm", "day_of_week", "hour_of_day", "month_of_year",
            "inter_tx_gap_norm", "rolling_tx_count_7d"]


def main():
    print("=" * 70)
    print("PHASE 6 — Temporal Graph Dataset Builder")
    print("=" * 70)

    print("\n[1/4] Loading and merging datasets...")
    df = load_and_merge_data()
    print(f"  - Loaded {len(df)} transactions")
    print(f"  - Timestamp range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  - Unique accounts: {df['account_id_x'].nunique()}")
    print(f"  - Unique devices: {df['device_id'].nunique()}")
    print(f"  - Unique IPs: {df['ip_address'].nunique()}")
    print(f"  - Unique merchants: {df['merchant_id'].nunique()}")

    print("\n[2/4] Computing temporal features...")
    df = compute_temporal_features(df)
    temp_cols = get_temporal_feature_cols()
    print(f"  - Temporal features added: {temp_cols}")
    print(f"  - t_norm range: [{df['t_norm'].min():.4f}, {df['t_norm'].max():.4f}]")
    print(f"  - inter_tx_gap_norm range: [{df['inter_tx_gap_norm'].min():.4f}, {df['inter_tx_gap_norm'].max():.4f}]")
    print(f"  - rolling_tx_count_7d max: {df['rolling_tx_count_7d'].max()}")

    print(f"\n[3/4] Building temporal graph (k={K_NEIGHBORS} neighbors)...")
    graph = build_temporal_graph(df, k=K_NEIGHBORS)
    neighbor_counts = [len(ns) for ns in graph["neighbors"]]
    isolated_count = sum(1 for c in neighbor_counts if c == 0)
    print(f"  - Nodes: {graph['n_nodes']}")
    print(f"  - Total directed edges: {graph['n_edges']}")
    print(f"  - Avg neighbors per node: {np.mean(neighbor_counts):.2f}")
    print(f"  - Max neighbors: {max(neighbor_counts)}")
    print(f"  - Isolated nodes (no predecessors): {isolated_count}")
    print(f"  - Edge type distribution:")
    edge_type_counts = {}
    for types in graph["edge_types"]:
        for et in types:
            edge_type_counts[et] = edge_type_counts.get(et, 0) + 1
    for et, cnt in sorted(edge_type_counts.items()):
        print(f"      {et}: {cnt} edges")

    print("\n[4/4] Verification...")
    assert graph["n_nodes"] == 2512, f"Expected 2512 nodes, got {graph['n_nodes']}"
    assert df["transaction_id"].nunique() == 2512, "Duplicate transaction IDs"
    assert df[ML_FEATURE_COLS].isnull().sum().sum() == 0, "Missing ML feature values"
    assert df["t_norm"].between(0.0, 1.0).all(), "t_norm out of range"
    # Verify no future leakage: for each transaction i, all neighbors j have j < i
    for i, neighbors in enumerate(graph["neighbors"]):
        for j in neighbors:
            assert j < i, f"Future leakage: edge {j} -> {i}"
    print("  [PASS] No future leakage in temporal graph")
    print("  [PASS] 2512 unique transactions")
    print("  [PASS] No missing ML features")
    print("  [PASS] Temporal features in valid range")

    print("\n[SUCCESS] Temporal graph dataset built successfully.")
    return df, graph


if __name__ == "__main__":
    main()
