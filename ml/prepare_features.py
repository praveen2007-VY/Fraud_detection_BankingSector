"""
Fraud Detection System — ML Feature Dataset Preparation for Unsupervised Anomaly Detection
File: ml/prepare_features.py

Purpose:
Deterministically extract, transform, and assemble the unsupervised ML feature dataset
from verified transactions (data/transactions_clean.csv) and graph metrics (neo4j/scored_transactions.csv).
Output: ml/features_unsupervised.csv (2,512 rows, 0 nulls, 0 infs).
"""

import os
import sys
import numpy as np
import pandas as pd

# Set deterministic behavior
SEED = 42
np.random.seed(SEED)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLEAN_CSV = os.path.join(PROJECT_ROOT, "data", "transactions_clean.csv")
SCORED_CSV = os.path.join(PROJECT_ROOT, "neo4j", "scored_transactions.csv")
OUTPUT_CSV = os.path.join(PROJECT_ROOT, "ml", "features_unsupervised.csv")


def prepare_unsupervised_features():
    print("[1/4] Loading input datasets...")
    df_clean = pd.read_csv(CLEAN_CSV)
    df_scored = pd.read_csv(SCORED_CSV)

    assert len(df_clean) == 2512, f"Expected 2512 clean rows, got {len(df_clean)}"
    assert len(df_scored) == 2512, f"Expected 2512 scored rows, got {len(df_scored)}"

    print("[2/4] Merging tabular transaction attributes and graph-derived metrics...")
    # Join on TransactionID == transaction_id
    merged = df_clean.merge(df_scored, left_on="TransactionID", right_on="transaction_id")
    assert len(merged) == 2512, f"Merge produced {len(merged)} rows, expected 2512"

    print("[3/4] Engineering ML features and binary encodings...")
    # Financial ratio: Transaction amount relative to account balance
    amount_to_balance_ratio = (merged["TransactionAmount"] / (merged["AccountBalance"] + 1.0)).round(6)

    # Categorical encodings:
    # 1. TransactionType: 'Debit' vs 'Credit'
    is_credit = (merged["TransactionType"] == "Credit").astype(int)

    # 2. Channel: One-hot encoding for delivery channel
    channel_atm = (merged["Channel"] == "ATM").astype(int)
    channel_online = (merged["Channel"] == "Online").astype(int)
    channel_branch = (merged["Channel"] == "Branch").astype(int)

    # Assemble structured DataFrame
    features_df = pd.DataFrame({
        # --- Identifiers & Traceability (Metadata: NOT used as ML training inputs) ---
        "transaction_id": merged["TransactionID"],
        "account_id": merged["AccountID"],

        # --- ML Feature Set: Raw Transaction Behaviors (5 features) ---
        "transaction_amount": merged["TransactionAmount"].astype(float),
        "transaction_duration": merged["TransactionDuration"].astype(int),
        "login_attempts": merged["LoginAttempts"].astype(int),
        "customer_age": merged["CustomerAge"].astype(int),
        "account_balance": merged["AccountBalance"].astype(float),

        # --- ML Feature Set: Financial Ratio Derived Behavior (1 feature) ---
        "amount_to_balance_ratio": amount_to_balance_ratio.astype(float),

        # --- ML Feature Set: Graph-Derived Topological Features (5 features) ---
        "shared_device_accounts": merged["shared_device_accounts"].astype(int),
        "shared_ip_accounts": merged["shared_ip_accounts"].astype(int),
        "merchant_cluster_accounts": merged["merchant_cluster_accounts"].astype(int),
        "rapid_velocity_count_24h": merged["rapid_velocity_count_24h"].astype(int),
        "account_network_sprawl_degree": merged["account_network_sprawl_degree"].astype(int),

        # --- ML Feature Set: Encoded Behavioral Categories (4 features) ---
        "is_credit": is_credit,
        "channel_atm": channel_atm,
        "channel_online": channel_online,
        "channel_branch": channel_branch,

        # --- Reference Benchmarks (Kept strictly for correlation/comparison, NOT ML inputs) ---
        "ref_approach_a_score": merged["approach_a_score"].astype(float),
        "ref_approach_b_score": merged["approach_b_score"].astype(float),
    })

    # Sort deterministically by transaction_id
    features_df = features_df.sort_values(by="transaction_id").reset_index(drop=True)

    print("[4/4] Validating feature data integrity...")
    assert len(features_df) == 2512, "Row count mismatch"
    assert features_df["transaction_id"].nunique() == 2512, "Duplicate TransactionID detected"
    assert features_df.isnull().sum().sum() == 0, "Missing values detected"
    assert not np.isinf(features_df.select_dtypes(include=[np.number]).values).any(), "Infinite values detected"

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    features_df.to_csv(OUTPUT_CSV, index=False)
    print(f"[SUCCESS] Exported {len(features_df)} rows and {len(features_df.columns)} columns to {OUTPUT_CSV}")

    return features_df


if __name__ == "__main__":
    prepare_unsupervised_features()
