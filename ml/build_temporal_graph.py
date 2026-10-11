"""
Fraud Detection System — Phase 6
File: ml/build_temporal_graph.py

Purpose:
    Standalone script to build and save the temporal graph dataset.
    Run this BEFORE training to prepare graph neighbor indices.
    Saves the neighbor index and temporal features to:
        ml/temporal_graph_cache.npz

CRITICAL CONSTRAINTS:
    - Real data only
    - No synthetic transactions
    - No fraud labels
    - Temporal ordering preserved
"""

import os
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "ml"))

from temporal_graph_data import (
    load_and_merge_data,
    compute_temporal_features,
    build_temporal_graph,
    ML_FEATURE_COLS,
    K_NEIGHBORS,
)

OUTPUT_CACHE = os.path.join(PROJECT_ROOT, "ml", "temporal_graph_cache.npz")


def main():
    print("=" * 70)
    print("PHASE 6 — Build Temporal Graph Cache")
    print("=" * 70)

    print("\n[1/5] Loading data...")
    df = load_and_merge_data()
    print(f"  Loaded {len(df)} transactions, sorted chronologically.")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    print("\n[2/5] Computing temporal features...")
    df = compute_temporal_features(df)
    print("  Temporal features computed:")
    for col in ["t_norm", "day_of_week", "hour_of_day", "month_of_year",
                 "inter_tx_gap_norm", "rolling_tx_count_7d"]:
        print(f"    {col}: min={df[col].min():.4f}, max={df[col].max():.4f}, "
              f"mean={df[col].mean():.4f}")

    print(f"\n[3/5] Building temporal graph (k={K_NEIGHBORS})...")
    graph = build_temporal_graph(df, k=K_NEIGHBORS)
    print(f"  Nodes: {graph['n_nodes']}")
    print(f"  Total temporal edges: {graph['n_edges']}")
    neighbor_counts = [len(ns) for ns in graph["neighbors"]]
    print(f"  Avg neighbors/node: {np.mean(neighbor_counts):.2f}")
    print(f"  Isolated nodes: {sum(1 for c in neighbor_counts if c == 0)}")

    print("\n[4/5] Preparing and saving cache arrays...")
    n = len(df)

    # Build padded neighbor matrix: shape (N, k) — padded with -1 for missing
    neighbor_matrix = np.full((n, K_NEIGHBORS), -1, dtype=np.int32)
    for i, neighbors in enumerate(graph["neighbors"]):
        for rank, j in enumerate(neighbors):
            neighbor_matrix[i, rank] = j

    # Save ML feature array (float32)
    X = df[ML_FEATURE_COLS].values.astype(np.float32)

    # Save temporal feature array
    temp_cols = ["t_norm", "day_of_week", "hour_of_day", "month_of_year",
                 "inter_tx_gap_norm", "rolling_tx_count_7d"]
    T = df[temp_cols].values.astype(np.float32)

    # Transaction IDs (for tracing)
    tx_ids = df["transaction_id"].values
    timestamps_unix = df["timestamp"].astype(np.int64).values  # nanoseconds since epoch

    # Reference scores (kept for comparison, NOT used in training)
    ref_a = df["approach_a_score"].values.astype(np.float32)
    ref_b = df["approach_b_score"].values.astype(np.float32)

    # Account IDs (for tracing)
    account_ids = df["account_id_x"].values

    np.savez_compressed(
        OUTPUT_CACHE,
        X=X,
        T=T,
        neighbor_matrix=neighbor_matrix,
        ref_a=ref_a,
        ref_b=ref_b,
        timestamps_unix=timestamps_unix,
    )
    # Save text arrays separately (numpy can't store variable-length strings in npz cleanly)
    tx_ids_path = os.path.join(PROJECT_ROOT, "ml", "temporal_graph_tx_ids.npy")
    acct_ids_path = os.path.join(PROJECT_ROOT, "ml", "temporal_graph_acct_ids.npy")
    np.save(tx_ids_path, tx_ids)
    np.save(acct_ids_path, account_ids)

    print(f"  Saved: {OUTPUT_CACHE}")
    print(f"    X shape: {X.shape}")
    print(f"    T shape: {T.shape}")
    print(f"    neighbor_matrix shape: {neighbor_matrix.shape}")
    print(f"  Saved tx_ids: {tx_ids_path}")
    print(f"  Saved acct_ids: {acct_ids_path}")

    print("\n[5/5] Verification...")
    assert X.shape == (2512, 15), f"X shape mismatch: {X.shape}"
    assert T.shape == (2512, 6), f"T shape mismatch: {T.shape}"
    assert neighbor_matrix.shape == (2512, K_NEIGHBORS), f"Neighbor matrix mismatch"
    assert not np.isnan(X).any(), "NaN in feature matrix"
    assert not np.isnan(T).any(), "NaN in temporal matrix"
    assert not np.isinf(X).any(), "Inf in feature matrix"
    print("  [PASS] Feature matrix shape: (2512, 15)")
    print("  [PASS] Temporal feature matrix shape: (2512, 6)")
    print(f"  [PASS] Neighbor matrix shape: (2512, {K_NEIGHBORS})")
    print("  [PASS] No NaN or Inf values")
    print("  [PASS] Temporal graph cache saved successfully")

    print("\n[SUCCESS] Temporal graph build complete.")
    return df, graph


if __name__ == "__main__":
    main()
